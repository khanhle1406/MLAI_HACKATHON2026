"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [filter, setFilter] = useState<"ALL" | "AUTO" | "ESCALATE" | "BLOCK">("ALL");

  useEffect(() => {
    fetch(`${API}/api/datasets`)
      .then((r) => r.json())
      .then((d) => {
        const list = d.datasets || [];
        setDatasets(list);
        setLoading(false);
        if (list.length > 0) {
          loadDetail(list[0].id);
        }
      })
      .catch(() => setLoading(false));
  }, []);

  const loadDetail = async (id: string) => {
    setLoadingDetail(true);
    try {
      const res = await fetch(`${API}/api/datasets/${id}`);
      const data = await res.json();
      setSelected(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingDetail(false);
    }
  };

  const filteredDecisions = (selected?.decisions || []).filter((d: any) => {
    if (filter === "ALL") return true;
    return d.decision === filter;
  });

  const assistantReport = selected?.assistant_report;

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold uppercase tracking-wider mb-2">
          <span>Kho Dữ Liệu & Báo Cáo Trợ Lý AI</span>
        </div>
        <h1 className="text-3xl md:text-4xl font-black text-white tracking-tight">
          Chi Tiết Bộ Dữ Liệu & Quyết Định Tự Chủ
        </h1>
        <p className="text-base text-slate-300 mt-1 max-w-3xl">
          Tra cứu toàn diện các phân tích của Trợ lý DataGuard: điểm chất lượng, các ca tự động sửa (AUTO), các ca chuyển tiếp con người (ESCALATE) và sổ cái thẩm quyền.
        </p>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Dataset Sidebar List */}
        <div className="col-span-12 lg:col-span-4 space-y-3">
          <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-4 backdrop-blur-md shadow-lg">
            <div className="pb-3 mb-2 border-b border-slate-800 flex items-center justify-between">
              <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                Tệp Đã Xử Lý ({datasets.length})
              </h2>
              <a href="/upload" className="text-xs text-emerald-400 font-semibold hover:underline">
                + Tải tệp mới
              </a>
            </div>

            {loading ? (
              <div className="p-8 text-center text-slate-400 text-sm">
                Đang tải danh sách...
              </div>
            ) : datasets.length === 0 ? (
              <div className="p-8 text-center space-y-2">
                <p className="text-slate-400 text-sm">Chưa có tệp nào.</p>
                <a href="/upload" className="text-emerald-400 text-sm font-semibold">
                  Tải lên ngay →
                </a>
              </div>
            ) : (
              <div className="space-y-1.5 max-h-[700px] overflow-y-auto pr-1">
                {datasets.map((ds) => {
                  const isSelected = selected?.id === ds.id;
                  return (
                    <button
                      key={ds.id}
                      onClick={() => loadDetail(ds.id)}
                      className={`w-full text-left p-4 rounded-xl transition-all border ${
                        isSelected
                          ? "bg-slate-800/90 border-emerald-500/50 shadow-md"
                          : "bg-slate-900/40 border-slate-800/60 hover:bg-slate-800/40 hover:border-slate-700"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <p className={`font-bold text-sm truncate ${isSelected ? "text-emerald-400" : "text-white"}`}>
                          {ds.filename}
                        </p>
                        <span className="text-[11px] font-mono text-slate-400 shrink-0">
                          {ds.summary?.total_rows} dòng
                        </span>
                      </div>

                      <div className="flex flex-wrap items-center gap-1.5 text-xs">
                        {(ds.summary?.auto_count ?? 0) > 0 && (
                          <span className="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 font-semibold text-[11px]">
                            ⚡ {ds.summary?.auto_count} AUTO
                          </span>
                        )}
                        {(ds.summary?.escalate_count ?? 0) > 0 && (
                          <span className="px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 font-semibold text-[11px]">
                            🔔 {ds.summary?.escalate_count} ESC
                          </span>
                        )}
                        {(ds.summary?.block_count ?? 0) > 0 && (
                          <span className="px-2 py-0.5 rounded bg-rose-500/15 text-rose-300 font-semibold text-[11px]">
                            🛑 {ds.summary?.block_count} BLK
                          </span>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Detail Panel */}
        <div className="col-span-12 lg:col-span-8">
          {loadingDetail ? (
            <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-16 text-center text-slate-400">
              <div className="w-8 h-8 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              Đang tải chi tiết bộ dữ liệu...
            </div>
          ) : !selected ? (
            <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-16 text-center text-slate-400">
              Chọn một bộ dữ liệu từ danh sách bên trái để xem báo cáo
            </div>
          ) : (
            <div className="space-y-6">
              {/* Executive Header Banner */}
              <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6 backdrop-blur-md shadow-xl space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 text-xs font-bold">
                        BÁO CÁO CHI TIẾT
                      </span>
                      <span className="text-xs text-slate-400 font-mono">
                        ID: {selected.id?.slice(0, 8)}...
                      </span>
                    </div>
                    <h2 className="text-2xl font-black text-white mt-1">
                      {selected.filename}
                    </h2>
                    <p className="text-sm text-slate-400">
                      {assistantReport?.domain_name || "Dữ liệu vận hành tổ chức"}
                    </p>
                  </div>

                  <div className="text-right shrink-0">
                    <p className="text-xs font-bold text-slate-400 uppercase">Sức Khỏe Dữ Liệu</p>
                    <p className="text-3xl font-black text-emerald-400">
                      {assistantReport?.cleanliness_score ?? 100}%
                    </p>
                    <p className="text-xs text-slate-400">
                      {selected.profile?.row_count} dòng × {selected.profile?.column_count} cột
                    </p>
                  </div>
                </div>

                {/* Assistant Narrative Quote */}
                {assistantReport?.assistant_briefing && (
                  <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/60 text-slate-200 text-sm leading-relaxed flex items-start gap-3">
                    <span className="text-2xl">🤖</span>
                    <p>{assistantReport.assistant_briefing}</p>
                  </div>
                )}
              </div>

              {/* Decisions & Actions Section */}
              <div className="bg-slate-900/60 rounded-2xl border border-slate-800 backdrop-blur-md shadow-xl overflow-hidden">
                <div className="p-5 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h3 className="text-lg font-bold text-white">
                      Danh Sách Quyết Định Xử Lý ({filteredDecisions.length})
                    </h3>
                    <p className="text-xs text-slate-400">
                      Mọi sửa đổi đều được kiểm soát nghiêm ngặt theo Cổng Tự Chủ
                    </p>
                  </div>

                  {/* Filter Pills */}
                  <div className="flex items-center gap-1.5 bg-slate-800/80 p-1 rounded-xl border border-slate-700">
                    {(["ALL", "AUTO", "ESCALATE", "BLOCK"] as const).map((f) => (
                      <button
                        key={f}
                        onClick={() => setFilter(f)}
                        className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                          filter === f
                            ? "bg-emerald-500 text-slate-950 shadow"
                            : "text-slate-300 hover:text-white"
                        }`}
                      >
                        {f === "ALL" ? "Tất Cả" : f}
                      </button>
                    ))}
                  </div>
                </div>

                {filteredDecisions.length === 0 ? (
                  <div className="p-12 text-center text-slate-400 text-sm">
                    Không có mục nào phù hợp bộ lọc "{filter}".
                  </div>
                ) : (
                  <div className="divide-y divide-slate-800/80 max-h-[600px] overflow-y-auto">
                    {filteredDecisions.map((d: any, i: number) => (
                      <div key={i} className="p-5 hover:bg-slate-800/30 transition-colors space-y-3">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div className="flex items-center gap-2.5">
                            <span
                              className={`px-2.5 py-0.5 rounded-md text-xs font-black uppercase ${
                                d.decision === "AUTO"
                                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                                  : d.decision === "ESCALATE"
                                  ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                                  : "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                              }`}
                            >
                              {d.decision}
                            </span>
                            <span className="text-sm font-bold text-white">
                              Dòng {d.row_id} • Cột <span className="font-mono text-cyan-300 font-bold">{d.column}</span>
                            </span>
                            {d.uncertainty_type && (
                              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                                [{d.uncertainty_type}]
                              </span>
                            )}
                          </div>

                          <div className="text-xs text-slate-400 flex items-center gap-3 font-mono">
                            <span>Bel(err)={d.belief_error?.toFixed(2)}</span>
                            <span>K={d.conflict_k?.toFixed(2)}</span>
                            <span>Bằng chứng: {d.evidence_count}</span>
                          </div>
                        </div>

                        {/* Values */}
                        <div className="flex items-center gap-3 text-sm p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                          <span className="text-xs text-slate-400 uppercase font-semibold">Giá trị cũ:</span>
                          <code className="px-2 py-0.5 rounded bg-slate-800 text-amber-300 font-mono font-bold">
                            "{d.old_value || "(rỗng)"}"
                          </code>
                          {d.new_value && (
                            <>
                              <span className="text-slate-500">→</span>
                              <span className="text-xs text-slate-400 uppercase font-semibold">Sửa thành:</span>
                              <code className="px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 font-mono font-bold border border-emerald-500/30">
                                "{d.new_value}"
                              </code>
                            </>
                          )}
                        </div>

                        {/* Escalation Question if present */}
                        {d.question && (
                          <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-slate-200">
                            <p className="font-bold text-amber-400 uppercase tracking-wider mb-1">
                              💬 Câu hỏi chuyển tiếp đến chuyên viên:
                            </p>
                            <p className="whitespace-pre-wrap leading-relaxed">
                              {d.question}
                            </p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Column Profiles Table */}
              {selected.profile?.columns && (
                <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6 backdrop-blur-md shadow-xl space-y-4">
                  <h3 className="text-lg font-bold text-white">
                    Hồ Sơ Toàn Bộ Cột Dữ Liệu ({selected.profile.columns.length})
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead>
                        <tr className="border-b border-slate-800 text-slate-400 text-xs uppercase font-bold">
                          <th className="py-2.5 px-3">Tên Cột</th>
                          <th className="py-2.5 px-3">Kiểu Quan Sát</th>
                          <th className="py-2.5 px-3">Kiểu Ngữ Nghĩa</th>
                          <th className="py-2.5 px-3 text-right">Missing</th>
                          <th className="py-2.5 px-3 text-right">Unique</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {selected.profile.columns.map((col: any, i: number) => (
                          <tr key={i} className="hover:bg-slate-800/30">
                            <td className="py-2.5 px-3 font-mono font-bold text-white">{col.column_name}</td>
                            <td className="py-2.5 px-3 font-mono text-xs text-slate-300">{col.observed_type}</td>
                            <td className="py-2.5 px-3">
                              {col.semantic_type ? (
                                <span className="px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 text-xs font-semibold">
                                  {col.semantic_type}
                                </span>
                              ) : (
                                <span className="text-slate-600">—</span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 text-right font-mono text-xs">
                              {(col.missing_rate * 100).toFixed(1)}%
                            </td>
                            <td className="py-2.5 px-3 text-right font-mono text-xs">
                              {(col.unique_rate * 100).toFixed(1)}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
