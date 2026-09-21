"""DataGuard Repair Execution Engine — executes validated AUTO repairs on datasets.

Applies deterministic, reversible repairs identified by the Autonomy Gate.
Records all modifications to the Audit Ledger with cryptographic signatures.
Produces a cleaned dataset while preserving original files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
import polars as pl

from core.audit.ledger import audit_ledger

logger = logging.getLogger(__name__)

STORAGE_DIR = Path("storage/cleaned")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def apply_auto_repairs(
    df: pl.DataFrame,
    decisions: list[dict[str, Any]],
    dataset_id: str,
    actor: str = "system_autonomy_gate",
) -> tuple[pl.DataFrame, dict[str, Any]]:
    """Apply all AUTO decisions to the dataframe.
    
    Returns:
        (repaired_df, repair_summary)
    """
    auto_decisions = [d for d in decisions if d.get("decision") == "AUTO" and d.get("new_value") is not None]
    
    if not auto_decisions:
        return df, {
            "total_repairs": 0,
            "columns_affected": [],
            "status": "NO_REPAIRS_NEEDED",
            "message": "Không có lỗi thường quy nào cần sửa tự động.",
        }

    # Work on a copy
    # To efficiently update cells in Polars, we can map columns
    repaired_cols = {}
    col_mods: dict[str, dict[int, str]] = {}
    
    for d in auto_decisions:
        col = d["column"]
        row = d["row_id"]
        new_val = d["new_value"]
        if col not in col_mods:
            col_mods[col] = {}
        col_mods[col][row] = str(new_val)

    # Apply modifications column by column
    exprs = []
    for col_name in df.columns:
        if col_name in col_mods:
            mods = col_mods[col_name]
            # Convert series to list, modify, convert back
            vals = df[col_name].cast(pl.Utf8).to_list()
            for r_idx, new_val in mods.items():
                if 0 <= r_idx < len(vals):
                    old_val = vals[r_idx]
                    vals[r_idx] = new_val
                    # Audit record
                    audit_ledger.record(
                        event_type="AUTO_REPAIR",
                        actor=actor,
                        dataset_id=dataset_id,
                        details={
                            "row_id": r_idx,
                            "column": col_name,
                            "old_value": old_val,
                            "new_value": new_val,
                            "action_type": "normalize",
                        },
                    )
            repaired_cols[col_name] = pl.Series(name=col_name, values=vals)
        else:
            repaired_cols[col_name] = df[col_name]

    repaired_df = pl.DataFrame(repaired_cols)
    
    # Save cleaned file
    cleaned_filename = f"{dataset_id}_cleaned.csv"
    cleaned_path = STORAGE_DIR / cleaned_filename
    repaired_df.write_csv(cleaned_path)

    summary = {
        "total_repairs": len(auto_decisions),
        "columns_affected": list(col_mods.keys()),
        "cleaned_file_url": f"/api/datasets/download-cleaned/{dataset_id}",
        "cleaned_filename": cleaned_filename,
        "status": "COMPLETED",
        "message": f"Đã tự động sửa thành công {len(auto_decisions)} lỗi trên {len(col_mods)} cột.",
    }
    logger.info(f"Applied {len(auto_decisions)} auto repairs to dataset {dataset_id}")
    return repaired_df, summary


def apply_human_edit(
    dataset_id: str,
    row_id: int,
    column: str | None,
    new_value: str | None,
    action: str = "EDIT",
    actor: str = "human_via_copilot",
    comment: str = "",
    original_df: pl.DataFrame | None = None,
) -> dict[str, Any]:
    """Execute a human review decision (EDIT, APPROVE, REJECT) requested via Chat Copilot."""
    from datetime import datetime
    cleaned_path = STORAGE_DIR / f"{dataset_id}_cleaned.csv"

    # Load either existing cleaned file or original df
    if cleaned_path.exists():
        curr_df = pl.read_csv(cleaned_path)
    elif original_df is not None:
        curr_df = original_df
    else:
        from apps.api.routers.datasets import _datasets
        d_info = _datasets.get(dataset_id, {})
        fp = d_info.get("file_path")
        if not fp or not Path(fp).exists():
            raise FileNotFoundError(f"Original dataset file for {dataset_id} not found")
        from core.ingestion.parser import parse_file
        curr_df, _ = parse_file(Path(fp))

    cols = curr_df.columns
    target_col = column
    
    # 1. Check direct column match
    if target_col and target_col in cols:
        matched_col = target_col
    else:
        # 2. Check alias mapping (e.g. 'lương' -> 'salary', 'tên' -> 'name', 'ngày' -> 'date')
        alias_map = {
            "lương": ["salary", "wage", "income", "compensation"],
            "luong": ["salary", "wage", "income", "compensation"],
            "tên": ["name", "full_name", "employee_name"],
            "ten": ["name", "full_name", "employee_name"],
            "email": ["email", "mail"],
            "phòng": ["department", "dept"],
            "phong": ["department", "dept"],
            "ngày": ["date", "created_at", "joined_date"],
            "ngay": ["date", "created_at", "joined_date"],
        }
        matched_col = None
        if target_col:
            t_low = target_col.lower()
            for k, aliases in alias_map.items():
                if k in t_low or t_low in k:
                    for a in aliases:
                        if a in cols:
                            matched_col = a
                            break
                if matched_col:
                    break

        # 3. If still not matched, check escalated decisions for this row_id
        if not matched_col:
            from apps.api.routers.datasets import _analysis_results
            analysis = _analysis_results.get(dataset_id, {})
            for d in analysis.get("decisions", []):
                if d.get("row_id") == row_id:
                    matched_col = d.get("column")
                    break

        # 4. Fallback: first non-id column
        if not matched_col or matched_col not in cols:
            matched_col = cols[1] if len(cols) > 1 else cols[0]

    target_col = matched_col

    old_value = None
    if 0 <= row_id < curr_df.height:
        old_value = curr_df[target_col][row_id]

    if action == "EDIT" and new_value is not None:
        vals = curr_df[target_col].cast(pl.Utf8).to_list()
        if 0 <= row_id < len(vals):
            vals[row_id] = str(new_value)
            curr_df = curr_df.with_columns(pl.Series(name=target_col, values=vals))
            curr_df.write_csv(cleaned_path)

    from apps.api.routers.reviews import _reviews
    from apps.api.routers.datasets import _analysis_results
    analysis = _analysis_results.get(dataset_id, {})
    matched_decision_id = None
    for d in analysis.get("decisions", []):
        if d.get("row_id") == row_id and (column is None or d.get("column") == target_col):
            matched_decision_id = d.get("decision_id")
            break

    if not matched_decision_id:
        matched_decision_id = f"dec_{dataset_id[:6]}_{row_id}_{target_col}"

    review_record = {
        "review_id": f"rv_{matched_decision_id[:8]}",
        "decision_id": matched_decision_id,
        "action": action,
        "edited_value": str(new_value) if action == "EDIT" else None,
        "comment": comment or f"Thực thi can thiệp qua Trợ lý Chat AI Copilot ({actor})",
        "reviewer": actor,
        "timestamp": datetime.utcnow().isoformat(),
    }
    _reviews[matched_decision_id] = review_record

    audit_ledger.record(
        event_type="HUMAN_REVIEW_CHAT",
        actor=actor,
        dataset_id=dataset_id,
        decision_id=matched_decision_id,
        details={
            "row_id": row_id,
            "column": target_col,
            "old_value": str(old_value) if old_value is not None else None,
            "new_value": str(new_value) if action == "EDIT" else None,
            "action": action,
            "comment": review_record["comment"],
        },
    )

    return {
        "status": "SUCCESS",
        "dataset_id": dataset_id,
        "decision_id": matched_decision_id,
        "row_id": row_id,
        "column": target_col,
        "old_value": str(old_value) if old_value is not None else None,
        "new_value": str(new_value) if action == "EDIT" else None,
        "action": action,
        "cleaned_file_url": f"/api/datasets/download-cleaned/{dataset_id}",
    }


def apply_batch_human_edit(
    dataset_id: str,
    column: str | None,
    new_value: str,
    target_rows: list[int] | None = None,
    action: str = "EDIT",
    actor: str = "human_via_copilot",
    comment: str = "",
    original_df: pl.DataFrame | None = None,
) -> dict[str, Any]:
    """Execute a batch human review edit across multiple escalated cells."""
    from datetime import datetime
    cleaned_path = STORAGE_DIR / f"{dataset_id}_cleaned.csv"

    if cleaned_path.exists():
        curr_df = pl.read_csv(cleaned_path)
    elif original_df is not None:
        curr_df = original_df
    else:
        from apps.api.routers.datasets import _datasets
        d_info = _datasets.get(dataset_id, {})
        fp = d_info.get("file_path")
        if not fp or not Path(fp).exists():
            raise FileNotFoundError(f"Original dataset file for {dataset_id} not found")
        from core.ingestion.parser import parse_file
        curr_df, _ = parse_file(Path(fp))

    cols = curr_df.columns
    from apps.api.routers.datasets import _analysis_results
    analysis = _analysis_results.get(dataset_id, {})
    decisions = analysis.get("decisions", [])

    # Resolve target column
    target_col = column
    if target_col and target_col not in cols:
        t_low = target_col.lower()
        for c in cols:
            if c.lower() == t_low or t_low in c.lower() or c.lower() in t_low:
                target_col = c
                break

    if not target_col or target_col not in cols:
        col_counts: dict[str, int] = {}
        for d in decisions:
            if d.get("decision") == "ESCALATE":
                c = d.get("column")
                if c in cols:
                    col_counts[c] = col_counts.get(c, 0) + 1
        if col_counts:
            target_col = max(col_counts, key=col_counts.get)
        else:
            target_col = cols[1] if len(cols) > 1 else cols[0]

    # Resolve target rows
    rows_to_edit = []
    if target_rows:
        rows_to_edit = [r for r in target_rows if 0 <= r < curr_df.height]
    else:
        for d in decisions:
            if d.get("column") == target_col:
                r = d.get("row_id")
                if r is not None and 0 <= r < curr_df.height and r not in rows_to_edit:
                    rows_to_edit.append(r)

    if not rows_to_edit:
        rows_to_edit = list(range(min(5, curr_df.height)))

    # Apply batch update in DataFrame
    vals = curr_df[target_col].cast(pl.Utf8).to_list()
    old_values = {}
    for r_idx in rows_to_edit:
        old_values[r_idx] = vals[r_idx]
        vals[r_idx] = str(new_value)

    curr_df = curr_df.with_columns(pl.Series(name=target_col, values=vals))
    curr_df.write_csv(cleaned_path)

    # Record in reviews and audit ledger
    from apps.api.routers.reviews import _reviews
    for r_idx in rows_to_edit:
        matched_decision_id = None
        for d in decisions:
            if d.get("row_id") == r_idx and d.get("column") == target_col:
                matched_decision_id = d.get("decision_id")
                break
        if not matched_decision_id:
            matched_decision_id = f"dec_{dataset_id[:6]}_{r_idx}_{target_col}"

        review_record = {
            "review_id": f"rv_{matched_decision_id[:8]}",
            "decision_id": matched_decision_id,
            "action": "EDIT",
            "edited_value": str(new_value),
            "comment": comment or f"Can thiệp hàng loạt qua Trợ lý Chat AI Copilot ({actor})",
            "reviewer": actor,
            "timestamp": datetime.utcnow().isoformat(),
        }
        _reviews[matched_decision_id] = review_record

        audit_ledger.record(
            event_type="HUMAN_REVIEW_CHAT",
            actor=actor,
            dataset_id=dataset_id,
            decision_id=matched_decision_id,
            details={
                "row_id": r_idx,
                "column": target_col,
                "old_value": str(old_values.get(r_idx)),
                "new_value": str(new_value),
                "action": "EDIT",
                "batch": True,
                "comment": review_record["comment"],
            },
        )

    return {
        "status": "SUCCESS",
        "dataset_id": dataset_id,
        "column": target_col,
        "rows_count": len(rows_to_edit),
        "rows": rows_to_edit,
        "new_value": str(new_value),
        "action": "BATCH_EDIT",
        "cleaned_file_url": f"/api/datasets/download-cleaned/{dataset_id}",
    }

