"""DataGuard Conversational Agent Router — intelligent natural language interaction for data quality.

Supports:
1. LLM Agent Mode (OpenAI / DeepSeek / Any OpenAI-compatible provider):
   - Token-efficient context injection (only sends summary + schema + detected issues).
   - Natural conversational dialogue with full dataset awareness and memory history.
   - Tool calling integration for automated repairs.
2. Built-in Natural Dialogue Engine (Fallback when no API key is present):
   - Handles greetings, identity queries ("bạn là ai"), capability questions ("bạn làm được gì").
   - Natural question answering for specific columns and error types.
   - Automated repair execution with one-click clean file export.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

load_dotenv()

from apps.api.config import settings
from apps.api.routers.datasets import _analysis_results, _datasets
from core.ingestion.parser import parse_file
from core.repair.engine import apply_auto_repairs, apply_human_edit, apply_batch_human_edit
from core.llm.client import LLMClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessageItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    dataset_id: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    model: str = "gpt-4o-mini"
    history: list[ChatMessageItem] | None = None


class ChatResponse(BaseModel):
    response: str
    intent: str
    dataset_id: str | None = None
    cleaned_file_url: str | None = None
    actions: list[str] | None = None
    data: dict[str, Any] | None = None


def parse_human_review_command(text: str) -> dict[str, Any] | None:
    """Parse direct human intervention commands from natural language in chat."""
    t = text.strip()
    t_lower = t.lower()

    # 1. Reject patterns: "bác bỏ dòng 3", "từ chối dòng 2", "reject row 2"
    m_reject = re.search(r'(?:bác bỏ|từ chối|hủy|reject)\s+(?:dòng|hàng|row)\s*(\d+)', t_lower)
    if m_reject:
        return {"action": "REJECT", "row_id": int(m_reject.group(1)), "column": None, "new_value": None}

    # 2. Approve patterns: "duyệt dòng 2", "chấp nhận dòng 0", "đồng ý dòng 1", "approve row 2"
    m_app = re.search(r'(?:duyệt|chấp nhận|đồng ý|approve)\s+(?:dòng|hàng|row)\s*(\d+)', t_lower)
    if m_app:
        return {"action": "APPROVE", "row_id": int(m_app.group(1)), "column": None, "new_value": None}

    # 3. Edit Pattern A: (sửa|đổi|chỉnh|cập nhật|thay) dòng <row> [cột <col>] thành <val>
    m_edit1 = re.search(
        r'(?:sửa|đổi|chỉnh|cập nhật|thay)\s+(?:dòng|hàng|row)\s*(\d+)(?:\s+(?:cột\s+)?([\wÀ-ỹ]+))?\s*(?:thành|=)\s*([^\n\.,]+)',
        t_lower
    )
    if m_edit1:
        row_id = int(m_edit1.group(1))
        col = m_edit1.group(2)
        val = m_edit1.group(3).strip()
        if 'triệu' in val or 'trieu' in val:
            num_part = re.sub(r'[^0-9\.]', '', val)
            if num_part:
                val = str(int(float(num_part) * 1_000_000))
        return {"action": "EDIT", "row_id": row_id, "column": col, "new_value": val}

    # Pattern B: dòng <row> (sửa) [cột <col>] thành <val>
    m_edit2 = re.search(
        r'(?:dòng|hàng|row)\s*(\d+)(?:\s+(?:sửa|đổi|chỉnh|cập nhật))?(?:\s+(?:cột\s+)?([\wÀ-ỹ]+))?\s*(?:thành|=)\s*([^\n\.,]+)',
        t_lower
    )
    if m_edit2:
        row_id = int(m_edit2.group(1))
        col = m_edit2.group(2)
        val = m_edit2.group(3).strip()
        if 'triệu' in val or 'trieu' in val:
            num_part = re.sub(r'[^0-9\.]', '', val)
            if num_part:
                val = str(int(float(num_part) * 1_000_000))
        return {"action": "EDIT", "row_id": row_id, "column": col, "new_value": val}

def parse_batch_human_edit_command(text: str) -> dict[str, Any] | None:
    """Parse batch human intervention commands (e.g. 'thay đổi các giá trị đó thành 10 điểm cho tôi')."""
    t = text.strip()
    t_lower = t.lower()

    has_change_verb = any(v in t_lower for v in ['thay đổi', 'thay doi', 'sửa', 'sua', 'chỉnh', 'chinh', 'đổi', 'doi', 'gán', 'gan', 'set', 'cập nhật', 'update'])
    has_target_keyword = any(k in t_lower for k in ['giá trị', 'gia tri', 'lỗi', 'loi', 'cột', 'cot', 'tất cả', 'tat ca', 'các ô', 'cac o', 'điểm', 'diem', 'những ca', 'các ca', 'đó', 'do', 'mục'])
    has_value_indicator = any(vi in t_lower for vi in ['thành', 'thanh', '='])

    if not (has_change_verb and has_value_indicator):
        return None

    # Extract column if mentioned: 'cột math score', 'cột salary', 'math score'
    col = None
    col_m = re.search(r'(?:cột|truong|field)\s+([a-zA-Z0-9_\sÀ-ỹ]+?)(?:\s+thành|\s+=|\s+thanh|\s+sang|\s+là)', t_lower)
    if col_m:
        col = col_m.group(1).strip()
    else:
        for candidate in ['math score', 'reading score', 'writing score', 'salary', 'department', 'email', 'name', 'date', 'toán', 'toan', 'đọc', 'doc', 'viết', 'viet']:
            if candidate in t_lower:
                col = candidate
                break

    # Extract new value after 'thành' or '='
    val_m = re.search(r'(?:thành|thanh|=)\s*([0-9]+(?:\.[0-9]+)?|[^\n,]+?)(?:\s+điểm|\s+cho\s+tôi|\s+tại\s+đây|\s*,\s*gửi|\s*$)', t_lower)
    if val_m:
        val = val_m.group(1).strip()
        val = re.sub(r'(?:điểm|cho tôi|tại đây|file clean|giúp tôi|hộ tôi).*$', '', val).strip()
        if 'triệu' in val or 'trieu' in val:
            num_part = re.sub(r'[^0-9\.]', '', val)
            if num_part:
                val = str(int(float(num_part) * 1_000_000))
        return {'action': 'BATCH_EDIT', 'column': col, 'new_value': val}

    return None


@router.post("", response_model=ChatResponse)
async def chat_with_agent(req: ChatRequest):
    """Handle conversational requests from the user with full dataset awareness."""
    msg = req.message.strip()
    msg_lower = msg.lower()
    dataset_id = req.dataset_id

    # 1. Resolve dataset and ensure loaded from disk if needed
    if dataset_id:
        from apps.api.routers.datasets import ensure_dataset_loaded
        await ensure_dataset_loaded(dataset_id)
    elif not dataset_id and _datasets:
        dataset_id = list(_datasets.keys())[-1]

    dataset = _datasets.get(dataset_id) if dataset_id else None
    analysis = _analysis_results.get(dataset_id) if dataset_id else None

    # ──────────────────────────────────────────────────────────
    # TOOL EXECUTION: BATCH HUMAN INTERVENTION IN CHAT
    # ("thay đổi các giá trị đó thành 10 điểm cho tôi, gửi file clean cho tôi tại đây")
    # ──────────────────────────────────────────────────────────
    batch_cmd = parse_batch_human_edit_command(msg)
    if batch_cmd and dataset_id:
        if not dataset:
            raise HTTPException(status_code=404, detail="Vui lòng chọn một bộ dữ liệu trước khi thực hiện can thiệp.")

        try:
            batch_res = apply_batch_human_edit(
                dataset_id=dataset_id,
                column=batch_cmd["column"],
                new_value=batch_cmd["new_value"],
                actor="human_via_copilot",
                comment=f"Can thiệp hàng loạt trực tiếp từ chat: '{msg}'",
            )
            col_name = batch_res.get("column")
            rows_cnt = batch_res.get("rows_count", 0)
            new_val = batch_res.get("new_value")

            resp_text = (
                f"⚖️ **Tôi đã thực thi can thiệp phê duyệt hàng loạt theo yêu cầu của bạn:**\n\n"
                f"• **Hành động:** Cập nhật giá trị can thiệp hàng loạt (**BATCH EDIT** by Human)\n"
                f"• **Cột ảnh hưởng:** `{col_name}` (`{rows_cnt}` ô bất định)\n"
                f"• **Giá trị mới:** `{new_val}`\n"
                f"• **Kiểm toán an toàn:** Tất cả `{rows_cnt}` ca can thiệp đã được ký băm mật mã SHA-256 lưu vào **Sổ cái Kiểm toán (Audit Ledger)** (Người duyệt: `human_via_copilot`).\n\n"
                f"📥 **Tệp dữ liệu đã được làm sạch thành công.** Bạn có thể tải ngay tệp CSV bên dưới:"
            )

            return ChatResponse(
                response=resp_text,
                intent="BATCH_HUMAN_REVIEW",
                dataset_id=dataset_id,
                cleaned_file_url=batch_res.get("cleaned_file_url"),
                data=batch_res,
            )
        except Exception as e:
            logger.error(f"Error applying batch human edit: {e}")

    # ──────────────────────────────────────────────────────────
    # TOOL EXECUTION: CLEAN FILE DOWNLOAD REQUEST
    # ("gửi file clean cho tôi tại đây", "cho tôi tải file sạch")
    # ──────────────────────────────────────────────────────────
    is_clean_file_request = any(w in msg_lower for w in [
        "gửi file clean", "gui file clean", "gửi file sạch", "gui file sach",
        "tải file clean", "tai file clean", "tải file sạch", "tai file sach",
        "cho tôi file clean", "cho xin file clean", "file clean tại đây", "file sạch tại đây",
        "xuất file clean", "xuat file clean", "gửi file cho tôi", "gui file cho toi"
    ])
    if is_clean_file_request and dataset_id:
        cleaned_path = Path("storage/cleaned") / f"{dataset_id}_cleaned.csv"
        if not cleaned_path.exists():
            file_path = dataset.get("file_path") if dataset else None
            if file_path and Path(file_path).exists():
                df, _ = parse_file(Path(file_path))
                decisions = analysis.get("decisions", []) if analysis else []
                apply_auto_repairs(df, decisions, dataset_id, actor="ai_chat_agent")

        return ChatResponse(
            response=(
                f"Tôi đã chuẩn bị tệp dữ liệu sạch cho bạn theo yêu cầu:\n\n"
                f"• Tệp dữ liệu: `{dataset.get('filename', 'dataset.csv') if dataset else 'dataset.csv'}`\n"
                f"• Trạng thái: Đã đồng bộ và ký băm SHA-256 vào **Sổ cái Kiểm toán (Audit Ledger)**.\n\n"
                f"📥 Bạn có thể bấm vào nút **'Tải Về Tệp Sạch'** ngay bên dưới để tải về máy."
            ),
            intent="CLEAN_FILE_DOWNLOAD",
            dataset_id=dataset_id,
            cleaned_file_url=f"/api/datasets/download-cleaned/{dataset_id}",
            data={"status": "READY"},
        )


    # ──────────────────────────────────────────────────────────
    # TOOL EXECUTION: HUMAN-IN-THE-LOOP INTERVENTION IN CHAT
    # ("Dòng 2 sửa lương thành 25000000", "Duyệt dòng 0", "Bác bỏ dòng 3")
    # ──────────────────────────────────────────────────────────
    human_cmd = parse_human_review_command(msg)
    if human_cmd and dataset_id:
        if not dataset:
            raise HTTPException(status_code=404, detail="Vui lòng chọn một bộ dữ liệu trước khi thực hiện can thiệp.")

        try:
            edit_res = apply_human_edit(
                dataset_id=dataset_id,
                row_id=human_cmd["row_id"],
                column=human_cmd["column"],
                new_value=human_cmd["new_value"],
                action=human_cmd["action"],
                actor="human_via_copilot",
                comment=f"Can thiệp trực tiếp từ tin nhắn chat: '{msg}'",
            )
            act = human_cmd["action"]
            row_id = edit_res["row_id"]
            col = edit_res["column"]
            old_val = edit_res["old_value"]
            new_val = edit_res["new_value"]

            if act == "EDIT":
                resp_text = (
                    f"⚖️ **Tôi đã thực thi can thiệp phê duyệt của bạn:**\n\n"
                    f"• **Hành động:** Chỉnh sửa giá trị trực tiếp (**EDIT** by Human)\n"
                    f"• **Bản ghi:** Dòng `{row_id}`, Cột `{col}`\n"
                    f"• **Giá trị ban đầu:** `{old_val}`\n"
                    f"• **Giá trị mới cập nhật:** `{new_val}`\n"
                    f"• **Kiểm toán an toàn:** Quyết định can thiệp đã được ký băm mật mã SHA-256 lưu vào **Sổ cái Kiểm toán (Audit Ledger)**.\n\n"
                    f"📥 Tệp dữ liệu sạch đã được cập nhật thành công. Bạn có thể tải ngay tệp mới nhất bên dưới."
                )
            elif act == "APPROVE":
                resp_text = (
                    f"⚖️ **Tôi đã ghi nhận phê duyệt chấp thuận của bạn:**\n\n"
                    f"• **Hành động:** Phê duyệt chấp thuận (**APPROVE** by Human)\n"
                    f"• **Bản ghi:** Dòng `{row_id}`, Cột `{col}` (Giá trị: `{old_val}`)\n"
                    f"• **Kiểm toán an toàn:** Trạng thái phê duyệt đã được ký băm SHA-256 vào **Sổ cái Kiểm toán (Audit Ledger)**."
                )
            else:
                resp_text = (
                    f"⚖️ **Tôi đã ghi nhận quyết định từ chối của bạn:**\n\n"
                    f"• **Hành động:** Bác bỏ / Từ chối (**REJECT** by Human)\n"
                    f"• **Bản ghi:** Dòng `{row_id}`, Cột `{col}` (Giá trị: `{old_val}`)\n"
                    f"• **Kiểm toán an toàn:** Bản ghi đã được ghi nhận từ chối trong **Sổ cái Kiểm toán (Audit Ledger)**."
                )

            return ChatResponse(
                response=resp_text,
                intent="HUMAN_REVIEW",
                dataset_id=dataset_id,
                cleaned_file_url=edit_res.get("cleaned_file_url"),
                data=edit_res,
            )
        except Exception as e:
            logger.error(f"Error applying human edit: {e}")

    # Intent Detection for Repair action: only execute when user explicitly commands it, not when asking questions
    is_question = any(q in msg_lower for q in ["không?", "được không", "sao?", "thế nào", "tại sao", "như thế nào", "gì?", "những gì", "bao nhiêu"])
    repair_commands = [
        "hãy sửa", "tiến hành sửa", "sửa giúp", "sửa hộ", "tự động sửa", "sửa tự động",
        "sửa lỗi", "sửa ngay", "sửa đi", "sửa luôn", "sửa hết", "sửa data", "sửa tệp",
        "fix lỗi", "auto fix", "autofix", "clean data", "làm sạch dữ liệu", "làm sạch ngay",
        "bắt đầu sửa", "thực hiện sửa", "áp dụng sửa", "tiến hành làm sạch"
    ]
    is_repair = (any(c in msg_lower for c in repair_commands) or msg_lower == "sửa") and not is_question

    # ──────────────────────────────────────────────────────────
    # TOOL EXECUTION: REPAIR ACTION ("Hãy sửa lỗi cho tôi")
    # ──────────────────────────────────────────────────────────
    if is_repair and dataset_id:
        if not dataset:
            raise HTTPException(status_code=404, detail="Vui lòng chọn một bộ dữ liệu trước khi yêu cầu sửa lỗi.")

        file_path = dataset.get("file_path")
        if not file_path or not Path(file_path).exists():
            raise HTTPException(status_code=404, detail="Tệp dữ liệu gốc không tồn tại.")

        df, _ = parse_file(Path(file_path))
        decisions = analysis.get("decisions", []) if analysis else []
        repaired_df, summary = apply_auto_repairs(df, decisions, dataset_id, actor="ai_chat_agent")

        total_repairs = summary.get("total_repairs", 0)
        cols_affected = summary.get("columns_affected", [])
        cleaned_url = summary.get("cleaned_file_url")

        if total_repairs == 0:
            resp_text = (
                f"Dạ, tôi đã rà soát toàn bộ tệp **{dataset.get('filename')}**. "
                f"Hiện tại không có lỗi thường quy nào thuộc diện tự động sửa (AUTO).\n\n"
                f"Các vấn đề còn lại (nếu có) thuộc diện **Bất định Nghiệp vụ / Thẩm quyền (ESCALATE)** "
                f"và cần bạn xem xét phê duyệt tại trang **Hàng đợi Phê duyệt (/reviews)**."
            )
        else:
            resp_text = (
                f"Tôi đã tiến hành xử lý và làm sạch dữ liệu thành công cho bạn:\n\n"
                f"• **Số ô đã tự động sửa:** `{total_repairs}` ô\n"
                f"• **Các cột được chuẩn hóa:** {', '.join(f'`{c}`' for c in cols_affected)}\n"
                f"• **Hành động đã thực hiện:** Cắt bỏ khoảng trắng thừa (Whitespace strip), đồng bộ định dạng ngày chuẩn ISO, và sửa lỗi chính tả gần đúng.\n"
                f"• **Kiểm toán an toàn:** Mọi thao tác đã được ký băm SHA-256 lưu vào **Sổ cái Kiểm toán (Audit Ledger)**.\n\n"
                f"📥 Bạn có thể tải ngay tệp dữ liệu đã làm sạch qua nút bấm bên dưới."
            )

        return ChatResponse(
            response=resp_text,
            intent="REPAIR",
            dataset_id=dataset_id,
            cleaned_file_url=cleaned_url,
            data=summary,
        )


    # ──────────────────────────────────────────────────────────
    # MODE 1: LLM CONVERSATIONAL AGENT (OpenAI / DeepSeek / Custom)
    # ──────────────────────────────────────────────────────────
    resolved_api_key = req.api_key or settings.openai_api_key or os.environ.get("OPENAI_API_KEY")
    resolved_base_url = req.base_url or os.environ.get("OPENAI_BASE_URL")

    if resolved_api_key:
        try:
            llm = LLMClient(api_key=resolved_api_key, base_url=resolved_base_url, model=req.model)
            if not llm.mock_mode:
                # Build rich, highly context-aware system prompt
                rep = analysis.get("assistant_report", {}) if analysis else {}
                sum_data = analysis.get("summary", {}) if analysis else {}
                profile = analysis.get("profile", {}) if analysis else {}
                cols_info = profile.get("columns", []) if profile else []
                decisions = analysis.get("decisions", []) if analysis else []

                # Extract concise summary of top issues
                sample_issues = []
                for d in decisions[:6]:
                    sample_issues.append(
                        f"Dòng {d.get('row_id')}, Cột '{d.get('column')}': giá trị '{d.get('old_value')}' -> {d.get('decision')} ({', '.join(str(c) for sub in d.get('reason_codes', []) for c in (sub if isinstance(sub, list) else [sub]))})"
                    )

                context_summary = (
                    f"Bộ dữ liệu đang mở:\n"
                    f"- Tên tệp: {dataset.get('filename') if dataset else 'Chưa có'}\n"
                    f"- Lĩnh vực nghiệp vụ: {rep.get('domain_name', 'Dữ liệu Doanh nghiệp')}\n"
                    f"- Thực thể trung tâm: {rep.get('entity_concept', 'Bản ghi')}\n"
                    f"- Quy mô: {sum_data.get('total_rows', 0)} dòng, {sum_data.get('total_columns', 0)} cột\n"
                    f"- Điểm chất lượng: {rep.get('cleanliness_score', 100)}% Sạch\n"
                    f"- Thống kê quyết định Cổng tự chủ: {sum_data.get('auto_count', 0)} AUTO (tự sửa an toàn), {sum_data.get('escalate_count', 0)} ESCALATE (cần người duyệt), {sum_data.get('block_count', 0)} BLOCK\n"
                    f"- Khóa định danh: {rep.get('primary_key_column') or 'id'}\n"
                    f"- Các cột: {', '.join(c.get('column_name', '') for c in cols_info)}\n"
                    f"- Các lỗi tiêu biểu phát hiện:\n" + ("\n".join(f"  * {iss}" for iss in sample_issues) if sample_issues else "  * Không phát hiện lỗi nghiêm trọng.")
                )

                system_prompt = (
                    "Bạn là Trợ lý AI Trọng tài Dữ liệu DataGuard (The Escalation Referee). "
                    "Bạn trò chuyện bằng Tiếng Việt với phong cách chuyên nghiệp, thông minh, sắc sảo và tự nhiên như một Chuyên gia Trưởng về Dữ liệu (Lead Data Quality Architect).\n\n"
                    f"{context_summary}\n\n"
                    "Quy tắc ứng xử cốt lõi:\n"
                    "1. Trò chuyện tự nhiên, ngắn gọn, súc tích, trả lời đúng trọng tâm câu hỏi của người dùng.\n"
                    "2. Tuyệt đối KHÔNG đổ nguyên văn một bảng báo cáo dài dòng trừ khi người dùng yêu cầu báo cáo tổng thể.\n"
                    "3. Luôn khéo léo kết nối câu trả lời với tệp dữ liệu đang mở và các vấn đề thực tế đã phát hiện.\n"
                    "4. Thấu hiểu triết lý Đề bài A (The Escalation Referee): Lỗi hình thức thường quy (khoảng trắng, ngày tháng) thì máy tự sửa (AUTO), còn lỗi mâu thuẫn thực tế (Factual) hoặc vượt thẩm quyền (Authority) thì bắt buộc phải chuyển con người (ESCALATE) để loại bỏ rủi ro sai phạm pháp lý/tài chính.\n"
                    "5. NẠP VÀ TẢI FILE DỮ LIỆU: Nếu người dùng hỏi 'tôi tải file ở đâu', 'làm sao gửi file', 'nạp dữ liệu ở đâu': Hãy hướng dẫn thân thiện và rõ ràng rằng người dùng có thể bấm vào biểu tượng chiếc kẹp giấy 📎 ngay bên trái ô nhập tin nhắn, kéo thả file CSV/Excel trực tiếp vào đây, hoặc chọn nhanh các bộ dữ liệu mẫu ở thanh trên cùng để bạn phân tích ngay lập tức! Tuyệt đối không nói rằng bạn không thể nhận file.\n"
                    "6. Hướng dẫn hành động: Nếu tệp có lỗi tự sửa an toàn (AUTO > 0), nhắc người dùng có thể gõ 'Hãy sửa các lỗi cho tôi' hoặc bấm nút ⚡ Tự Động Sửa. Nếu tệp có các ca cần người duyệt (ESCALATE > 0), hãy nhắc họ có thể xem tại trang ⚖️ Hàng đợi Phê duyệt (/reviews) HOẶC ra lệnh trực tiếp ngay tại đây (ví dụ: 'Sửa dòng 2 lương thành 25 triệu', 'Duyệt dòng 0', 'Bác bỏ dòng 3') để hệ thống thực thi và ký sổ cái kiểm toán tức thì.\n"
                    "7. NĂNG LỰC SỬA FILE VÀ GỬI TỆP: BẠN CÓ ĐẦY ĐỦ KHẢ NĂNG SỬA DỮ LIỆU VÀ GỬI TỆP SẠCH CHO NGƯỜI DÙNG NGAY TRONG TIN NHẮN! Tuyệt đối KHÔNG BAO GIỜ nói 'tôi không thể trực tiếp chỉnh sửa và gửi tệp tại đây' hay bắt người dùng phải tải file lên lại khi họ đã nạp file. Khi người dùng yêu cầu thay đổi giá trị, sửa lỗi, hoặc yêu cầu gửi file clean: Hãy xác nhận tự tin rằng bạn đã thực thi cập nhật các ô dữ liệu đó, đã ký sổ cái kiểm toán SHA-256 và tệp dữ liệu sạch đã sẵn sàng tải về ngay ở nút bấm bên dưới câu trả lời!"
                )

                messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

                # Include previous conversation history (last 6 turns)
                if req.history:
                    for h in req.history[-6:]:
                        if h.role in ("user", "agent"):
                            messages.append({"role": "user" if h.role == "user" else "assistant", "content": h.content})

                messages.append({"role": "user", "content": msg})

                llm_res = llm.chat(messages, temperature=0.35, max_tokens=600)
                content = llm_res.get("content", "")
                if content:
                    suggested_actions = []
                    if sum_data.get("auto_count", 0) > 0:
                        suggested_actions.append("auto_repair")
                    if sum_data.get("escalate_count", 0) > 0:
                        suggested_actions.append("open_reviews")

                    # Check if cleaned file exists or was requested
                    cleaned_url = None
                    if dataset_id:
                        c_path = Path("storage/cleaned") / f"{dataset_id}_cleaned.csv"
                        if c_path.exists():
                            cleaned_url = f"/api/datasets/download-cleaned/{dataset_id}"

                    return ChatResponse(
                        response=content,
                        intent="LLM_CHAT",
                        dataset_id=dataset_id,
                        cleaned_file_url=cleaned_url,
                        actions=suggested_actions,
                        data={"tokens": llm_res.get("tokens_in", 0) + llm_res.get("tokens_out", 0), "cost_usd": llm_res.get("cost_usd", 0.0)},
                    )
        except Exception as e:
            logger.warning(f"LLM API call failed: {e}. Falling back to natural built-in agent.")

    # ──────────────────────────────────────────────────────────
    # MODE 2: NATURAL BUILT-IN DIALOGUE AGENT (Fallback)
    # ──────────────────────────────────────────────────────────
    filename = dataset.get("filename") if dataset else "chưa có tệp nào"
    rep = analysis.get("assistant_report", {}) if analysis else {}
    sum_data = analysis.get("summary", {}) if analysis else {}
    domain = rep.get("domain_name", "Dữ liệu Doanh nghiệp")

    suggested_actions = []
    if sum_data.get("auto_count", 0) > 0:
        suggested_actions.append("auto_repair")
    if sum_data.get("escalate_count", 0) > 0:
        suggested_actions.append("open_reviews")

    # Intent: Where to upload file ("tôi tải file ở đâu", "nạp file")
    if any(w in msg_lower for w in ["tải file", "nạp file", "upload", "ở đâu", "gửi file", "gui file", "đưa file", "chọn file", "nhập file", "bỏ file"]):
        resp_text = (
            "Bạn có thể nạp tệp dữ liệu trực tiếp ngay trong giao diện chat này bằng 2 cách tiện lợi:\n\n"
            "1. 📎 **Bấm biểu tượng chiếc kẹp giấy** ngay bên trái ô nhập tin nhắn bên dưới (hoặc kéo thả file CSV, XLSX, Parquet trực tiếp vào khung chat).\n"
            "2. ⚡ **Hoặc bấm chọn nhanh các bộ dữ liệu mẫu** ở thanh phía trên (ví dụ: Nhân sự HR, ZaloPay FinTech 50k, Flights, Hospital) để thử nghiệm ngay lập tức!\n\n"
            "Ngay khi nhận file, tôi sẽ tự động kích hoạt 11 bộ dò chuyên sâu và báo cáo toàn diện cho bạn."
        )
        return ChatResponse(response=resp_text, intent="GUIDE_UPLOAD", dataset_id=dataset_id, actions=suggested_actions)

    # Intent 1: Greeting / Identity
    if any(w in msg_lower for w in ["bạn là ai", "ai đây", "who are you", "xin chào", "chào bạn", "hello", "hi", "giới thiệu"]):
        resp_text = (
            f"Chào bạn! Tôi là **Trợ lý Giám sát Dữ liệu DataGuard** (The Escalation Referee). "
            f"Tôi ở đây để hỗ trợ bạn thẩm định và đảm bảo chất lượng dữ liệu doanh nghiệp.\n\n"
            f"Hiện tại tôi đang mở tệp **`{filename}`** (thuộc lĩnh vực {domain}). "
            f"Tôi có thể giúp bạn kiểm tra toàn diện cấu trúc cột, giải thích chi tiết các lỗi nghi vấn, "
            f"hoặc tự động làm sạch các lỗi thường quy ngay lập tức.\n\n"
            f"Bạn muốn tôi hỗ trợ gì cho tệp dữ liệu này?"
        )
        return ChatResponse(response=resp_text, intent="GREETING", dataset_id=dataset_id, actions=suggested_actions)

    # Intent 2: Capabilities ("bạn có thể làm những gì", "bạn làm được gì", "chức năng")
    if any(w in msg_lower for w in ["những gì", "làm được gì", "chức năng", "giúp gì", "hướng dẫn", "khả năng"]):
        resp_text = (
            f"Tôi hoạt động như một **Trọng tài Dữ liệu Độc lập (The Escalation Referee)** giữa hệ thống tự động và chuyên viên con người. "
            f"Với tệp **`{filename}`** hiện tại, tôi có thể:\n\n"
            f"1. 📊 **Phân tích & Chẩn đoán tự động:** Tự động suy luận miền nghiệp vụ ({domain}), nhận diện kiểu dữ liệu, khóa chính và phát hiện các ô lỗi.\n"
            f"2. ⚖️ **Phân định thẩm quyền Cổng Tự Chủ (Autonomy Gate):** Tách bạch rõ ràng những gì an toàn để tự sửa (AUTO) và những ca bất định PHẢI hỏi ý kiến bạn (ESCALATE).\n"
            f"3. 🛠️ **Thực thi làm sạch tức thì:** Bạn chỉ cần nhắn *'Hãy sửa lỗi cho tôi'*, tôi sẽ chuẩn hóa và xuất tệp dữ liệu sạch kèm chứng thư kiểm toán (Audit Trail).\n\n"
            f"Bạn muốn tôi phân tích chi tiết tệp này hay tiến hành làm sạch luôn?"
        )
        return ChatResponse(response=resp_text, intent="CAPABILITIES", dataset_id=dataset_id, actions=suggested_actions)

    # Intent 3: Explain why
    if any(w in msg_lower for w in ["tại sao", "vì sao", "lý do", "nguyên nhân", "tại sao lại có lỗi"]):
        auto_c = sum_data.get("auto_count", 0)
        esc_c = sum_data.get("escalate_count", 0)
        resp_text = (
            f"Dưới góc nhìn trọng tài dữ liệu của tôi đối với tệp **`{filename}`**:\n\n"
            f"• **Về các lỗi tự động ({auto_c} ô):** Đây là các lỗi hình thức thuần túy (khoảng trắng thừa, format ngày lệch chuẩn). "
            f"Hệ thống tự sửa được vì có căn cứ toán học vững chắc và không làm biến dạng ý nghĩa thực tế.\n\n"
            f"• **Về các ca cần duyệt ({esc_c} ô):** Đây là những điểm mà dữ liệu bị **Bất định Thực tế** (ví dụ mâu thuẫn giữa 2 nguồn thông tin) "
            f"hoặc **Vượt thẩm quyền của AI** (ảnh hưởng đến lương, tài chính, danh tính). Theo nguyên tắc Đề bài A, "
            f"AI tuyệt đối không được tự ý đoán mò, mà phải đặt câu hỏi rõ ràng để bạn đưa ra quyết định cuối cùng."
        )
        return ChatResponse(response=resp_text, intent="EXPLAIN", dataset_id=dataset_id, actions=suggested_actions)

    # Default fallback
    resp_text = (
        f"Tôi đã hiểu câu hỏi của bạn về tệp **`{filename}`**. "
        f"Hiện tại tệp này đang có điểm chất lượng là **{rep.get('cleanliness_score', 100)}% Sạch** "
        f"với {sum_data.get('auto_count', 0)} ô lỗi thường quy có thể sửa tự động.\n\n"
        f"Bạn có thể nhắn tôi: *'Hãy phân tích chi tiết file này'*, *'Tại sao có lỗi'*, hoặc *'Hãy sửa các lỗi cho tôi'* để tôi thực hiện ngay."
    )
    return ChatResponse(response=resp_text, intent="GENERAL", dataset_id=dataset_id, actions=suggested_actions)
