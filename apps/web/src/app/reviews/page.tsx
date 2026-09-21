"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ReviewsPage() {
  const [reviews, setReviews] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState<string | null>(null);

  const loadReviews = () => {
    fetch(`${API}/api/reviews`)
      .then((r) => r.json())
      .then((d) => {
        setReviews(d.queue || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadReviews();
  }, []);

  const handleAction = async (decisionId: string, action: "approve" | "reject") => {
    setProcessingId(decisionId);
    try {
      await fetch(`${API}/api/reviews/${decisionId}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: action.toUpperCase(),
          reviewer: "human_supervisor",
          comment: `Quyết định duyệt ${action.toUpperCase()} từ giao diện điều hành`,
        }),
      });
      loadReviews();
    } catch (e) {
      console.error(e);
    } finally {
      setProcessingId(null);
    }
  };

  const getUncertaintyBadge = (type: string) => {
    switch (type) {
      case "FACTUAL":
        return {
          label: "Bất Định Sự Thật (Factual)",
          desc: "Chưa xác định được thông tin thực tế từ ngữ cảnh",
          color: "bg-amber-500/15 text-amber-300 border-amber-500/30",
        };
      case "POLICY":
        return {
          label: "Chưa Có Quy Định (Policy)",
          desc: "Nằm ngoài phạm vi quy chế hiện hành của tổ chức",
          color: "bg-blue-500/15 text-blue-300 border-blue-500/30",
        };
      case "AUTHORITY":
        return {
          label: "Vượt Thẩm Quyền (Authority)",
          desc: "Dữ liệu mật/tài chính nhạy cảm vượt quyền của AI",
          color: "bg-rose-500/15 text-rose-300 border-rose-500/30",
        };
      default:
        return {
          label: type || "Nghi Vấn",
          desc: "Cần chuyên viên xác nhận",
          color: "bg-slate-800 text-slate-300 border-slate-700",
        };
    }
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-semibold uppercase tracking-wider mb-2">
          <span>Human-in-the-Loop • Trách Nhiệm Giải Trình</span>
        </div>
        <h1 className="text-3xl md:text-4xl font-black text-white tracking-tight">
          Hàng Đợi Phê Duyệt Nghiệp Vụ
        </h1>
        <p className="text-base text-slate-300 mt-2 max-w-3xl leading-relaxed">
          Nơi tập trung các trường hợp mà Trợ lý AI nhận diện mức độ bất định hoặc vượt ranh giới thẩm quyền, chủ động dừng tự động hóa để xin quyết định dứt khoát từ con người.
        </p>
      </div>

      {loading ? (
        <div className="p-16 text-center text-slate-400">
          <div className="w-8 h-8 border-2 border-amber-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          Đang tải hàng đợi xem xét...
        </div>
      ) : reviews.length === 0 ? (
        <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-16 text-center space-y-4 backdrop-blur-md shadow-xl">
          <div className="text-6xl">🎉</div>
          <h3 className="text-2xl font-bold text-white">
            Không Có Mục Nào Đang Chờ Phê Duyệt
          </h3>
          <p className="text-base text-slate-400 max-w-md mx-auto">
            Mọi lỗi thường quy đã được tự động xử lý an toàn. Hãy tải lên bộ dữ liệu mới có chứa trường hợp nghi vấn để tạo hàng đợi duyệt.
          </p>
          <div className="pt-2">
            <a
              href="/upload"
              className="inline-flex px-6 py-3 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-sm transition-colors"
            >
              Tải Dữ Liệu Lên →
            </a>
          </div>
        </div>
      ) : (
        <div className="space-y-5">
          <div className="flex items-center justify-between text-sm text-slate-400 pb-1">
            <span>
              Tổng cộng: <strong className="text-white">{reviews.length}</strong> trường hợp cần duyệt
            </span>
            <span className="text-xs italic">
              Tiêu chuẩn Đề bài A: Mỗi câu hỏi phải cụ thể, người duyệt có thể quyết định ngay
            </span>
          </div>

          {reviews.map((r, i) => {
            const badge = getUncertaintyBadge(r.uncertainty_type);
            const isProcessing = processingId === r.decision_id;

            return (
              <div
                key={i}
                className="bg-slate-900/70 rounded-2xl border border-slate-800 hover:border-slate-700 p-6 backdrop-blur-md shadow-xl transition-all space-y-4"
              >
                {/* Top classification row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
                  <div className="flex flex-wrap items-center gap-2.5">
                    <span className={`px-3 py-1 rounded-lg text-xs font-black uppercase tracking-wider border ${badge.color}`}>
                      {badge.label}
                    </span>
                    <span className="text-sm font-bold text-white">
                      Dòng {r.row_id} • Cột <span className="font-mono text-cyan-300">{r.column}</span>
                    </span>
                  </div>

                  <div className="text-xs text-slate-400 font-mono">
                    Bel(err)={r.belief_error?.toFixed(2)} • Ign={r.ignorance?.toFixed(2)}
                  </div>
                </div>

                {/* Value context */}
                <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 flex items-center gap-3 text-sm">
                  <span className="text-xs text-slate-400 uppercase font-semibold">Giá trị đang nghi vấn:</span>
                  <code className="px-2.5 py-1 rounded bg-slate-800 text-amber-300 font-mono font-bold text-base">
                    "{r.old_value || "(rỗng)"}"
                  </code>
                </div>

                {/* Specific Actionable Question */}
                {r.question && (
                  <div className="p-5 rounded-xl bg-amber-500/10 border border-amber-500/20 space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="text-base">❓</span>
                      <p className="text-xs font-bold text-amber-400 uppercase tracking-wider">
                        Câu Hỏi Chi Tiết Từ Trợ Lý AI:
                      </p>
                    </div>
                    <p className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
                      {r.question}
                    </p>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="pt-2 flex items-center justify-between">
                  <p className="text-xs text-slate-400">
                    {badge.desc}
                  </p>

                  <div className="flex items-center gap-3">
                    {!r.reviewed ? (
                      <>
                        <button
                          onClick={() => handleAction(r.decision_id, "reject")}
                          disabled={isProcessing}
                          className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-rose-900/30 text-rose-300 hover:text-rose-200 text-sm font-bold border border-slate-700 hover:border-rose-500/50 transition-all cursor-pointer disabled:opacity-50"
                        >
                          ✕ Giữ Nguyên (Reject Fix)
                        </button>
                        <button
                          onClick={() => handleAction(r.decision_id, "approve")}
                          disabled={isProcessing}
                          className="px-6 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-sm font-black transition-all shadow-lg shadow-emerald-500/20 cursor-pointer disabled:opacity-50"
                        >
                          ✓ Phê Duyệt Sửa (Approve)
                        </button>
                      </>
                    ) : (
                      <span className="px-4 py-2 rounded-xl bg-slate-800 text-slate-400 text-xs font-semibold border border-slate-700">
                        ✓ Đã Phê Duyệt
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
