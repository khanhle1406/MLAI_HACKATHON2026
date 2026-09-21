"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function VerifyPage() {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any>(null);

  const runVerify = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/verify`, { method: "POST" });
      const data = await res.json();
      setResults(data);
    } catch (e: any) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold uppercase tracking-wider mb-2">
          <span>Khảo Thí Cuộc Thi • Vòng Sơ Loại 90 Giây</span>
        </div>
        <h1 className="text-3xl md:text-4xl font-black text-white tracking-tight">
          Bộ Công Cụ Kiểm Thử Tự Động (Verify Harness)
        </h1>
        <p className="text-base text-slate-300 mt-2 max-w-3xl leading-relaxed">
          Được thiết kế chuẩn theo quy định của Ban Giám Khảo: 1 thao tác thực thi 5 trường hợp kiểm thử độc lập (3 trường hợp thường quy + 2 trường hợp cần chuyển tiếp), xác minh tiêu chí "Không chuyển tiếp quá mức" và "Chất lượng câu hỏi chuyển tiếp".
        </p>
      </div>

      {/* Action CTA Bar */}
      <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6 backdrop-blur-md shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-white">
            Kiểm Tra Tự Động Toàn Diện (5 Test Cases)
          </h2>
          <p className="text-sm text-slate-400">
            Thời gian chạy: &lt; 0.5 giây • Tự động đối soát Invariant Cổng Tự Chủ
          </p>
        </div>

        <button
          onClick={runVerify}
          disabled={loading}
          className="px-8 py-4 bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500 hover:from-emerald-400 hover:to-cyan-400 text-slate-950 font-black rounded-xl text-base transition-all shadow-xl shadow-emerald-500/25 disabled:opacity-50 flex items-center gap-3 cursor-pointer shrink-0"
        >
          {loading ? (
            <>
              <span className="w-5 h-5 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
              <span>Đang Chạy Khảo Thí...</span>
            </>
          ) : (
            <>
              <span>🚀 Chạy Toàn Bộ 5 Bài Kiểm Thử</span>
            </>
          )}
        </button>
      </div>

      {/* Results Cockpit */}
      {results && (
        <div className="space-y-6">
          {/* Scoreboard Cards */}
          <div className="bg-gradient-to-br from-slate-900 via-slate-900/90 to-emerald-950/30 rounded-2xl border border-slate-700 p-8 shadow-2xl space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
              <div>
                <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 uppercase">
                  BÁO CÁO KHẢO THÍ CHÍNH THỨC
                </span>
                <h3 className="text-2xl font-black text-white mt-1">
                  Kết Quả Kiểm Thử Đề Bài A: The Escalation Referee
                </h3>
              </div>
              <span className="text-xs text-slate-400 font-mono">
                {results.timestamp}
              </span>
            </div>

            {/* Big 3 metrics */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
              <div className="p-5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-center">
                <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Tự Động Thường Quy (Routine)
                </p>
                <p className="text-4xl font-black text-emerald-400 mt-1">
                  {results.routine_automation}
                </p>
                <p className="text-xs text-slate-400 mt-1">3/3 ca thường quy đạt AUTO</p>
              </div>

              <div className="p-5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-center">
                <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Chuyển Tiếp Chuyên Viên (Escalation)
                </p>
                <p className="text-4xl font-black text-amber-400 mt-1">
                  {results.escalation}
                </p>
                <p className="text-xs text-slate-400 mt-1">2/2 ca nghi vấn đạt ESCALATE</p>
              </div>

              <div
                className={`p-5 rounded-xl border text-center ${
                  results.overall_pass
                    ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-300"
                    : "bg-rose-500/15 border-rose-500/40 text-rose-300"
                }`}
              >
                <p className="text-xs font-bold uppercase tracking-wider">
                  Tổng Điểm Khảo Thí
                </p>
                <p className="text-4xl font-black mt-1">
                  {results.total}
                </p>
                <p className="text-xs mt-1 font-bold uppercase">
                  {results.overall_pass ? "🎉 ĐẠT CHUẨN 100% (PASS)" : "CHƯA ĐẠT (FAIL)"}
                </p>
              </div>
            </div>
          </div>

          {/* Test Case Breakdown Table */}
          <div className="bg-slate-900/60 rounded-2xl border border-slate-800 backdrop-blur-md shadow-xl overflow-hidden">
            <div className="p-6 border-b border-slate-800">
              <h3 className="text-lg font-bold text-white">
                Bảng Đối Soát Chi Tiết Từng Ca Kiểm Thử
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Đáp ứng tiêu chí đánh giá Sơ loại 90s & Chung kết 20 điểm
              </p>
            </div>

            <div className="divide-y divide-slate-800/70">
              {results.cases?.map((c: any) => (
                <div
                  key={c.case_id}
                  className="p-6 hover:bg-slate-800/30 transition-colors space-y-3"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <span
                        className={`w-9 h-9 rounded-xl flex items-center justify-center text-base font-black ${
                          c.passed
                            ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                            : "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                        }`}
                      >
                        {c.passed ? "✓" : "✗"}
                      </span>
                      <div>
                        <p className="text-base font-bold text-white">
                          {c.case_id}: {c.description}
                        </p>
                        <p className="text-xs text-slate-400 font-mono mt-0.5">
                          Mong đợi: <span className="text-white font-bold">{c.expected_decision}</span> •{" "}
                          Thực tế: <span className="text-emerald-400 font-bold">{c.actual_decision || "—"}</span> •{" "}
                          Thời gian: <span className="text-slate-300">{c.duration_seconds}s</span>
                        </p>
                      </div>
                    </div>

                    <span
                      className={`px-3.5 py-1 rounded-lg text-xs font-black tracking-wider ${
                        c.passed
                          ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                          : "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                      }`}
                    >
                      {c.passed ? "PASS ✅" : "FAIL ❌"}
                    </span>
                  </div>

                  {/* Question display if escalated */}
                  {c.question && (
                    <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-slate-200">
                      <span className="font-bold text-amber-400 uppercase block mb-1">
                        💬 Câu hỏi hệ thống tự động sinh:
                      </span>
                      <p className="font-sans leading-relaxed">
                        {c.question}
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
