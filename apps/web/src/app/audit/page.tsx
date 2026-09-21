"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AuditPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("ALL");

  useEffect(() => {
    fetch(`${API}/api/audit?limit=100`)
      .then((r) => r.json())
      .then((d) => {
        setEvents(d.events || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const typeStyles: Record<string, { label: string; color: string }> = {
    UPLOAD: { label: "Tải Tệp", color: "bg-blue-500/15 text-blue-300 border-blue-500/30" },
    PROFILE: { label: "Hồ Sơ Hóa", color: "bg-purple-500/15 text-purple-300 border-purple-500/30" },
    DETECT: { label: "Bộ Dò Quét", color: "bg-indigo-500/15 text-indigo-300 border-indigo-500/30" },
    AUTO: { label: "Tự Động Sửa", color: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" },
    ESCALATE: { label: "Chuyển Tiếp", color: "bg-amber-500/15 text-amber-300 border-amber-500/30" },
    BLOCK: { label: "Tạm Chặn", color: "bg-rose-500/15 text-rose-300 border-rose-500/30" },
    REVIEW: { label: "Con Người Duyệt", color: "bg-cyan-500/15 text-cyan-300 border-cyan-500/30" },
    DELETE: { label: "Xóa Dữ Liệu", color: "bg-slate-700 text-slate-300 border-slate-600" },
  };

  const filteredEvents = events.filter((ev) => {
    if (filter === "ALL") return true;
    return ev.event_type === filter;
  });

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-semibold uppercase tracking-wider mb-2">
          <span>Sổ Cái Minh Bạch • Trách Nhiệm Giải Trình</span>
        </div>
        <h1 className="text-3xl md:text-4xl font-black text-white tracking-tight">
          Sổ Cái Kiểm Toán Toàn Vẹn (Audit Ledger)
        </h1>
        <p className="text-base text-slate-300 mt-2 max-w-3xl leading-relaxed">
          Ghi nhận toàn bộ hành động của hệ thống theo thời gian thực: Ai thực hiện, vào thời điểm nào, trên đối tượng nào và lý do tương ứng. Tuân thủ tiêu chuẩn bất biến và pháp chế doanh nghiệp.
        </p>
      </div>

      {/* Filter Chips Bar */}
      <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-4 backdrop-blur-md shadow-lg flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mr-1">
            Lọc Sự Kiện:
          </span>
          {["ALL", "AUTO", "ESCALATE", "BLOCK", "REVIEW", "UPLOAD", "PROFILE"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all ${
                filter === f
                  ? "bg-emerald-500 text-slate-950 shadow-md"
                  : "bg-slate-800/80 text-slate-300 hover:bg-slate-700"
              }`}
            >
              {f === "ALL" ? "Tất Cả" : f}
            </button>
          ))}
        </div>
        <span className="text-xs text-slate-400 font-mono">
          Hiển thị: <strong className="text-white">{filteredEvents.length}</strong> / {events.length} bản ghi
        </span>
      </div>

      {/* Events Table / Timeline */}
      <div className="bg-slate-900/60 rounded-2xl border border-slate-800 backdrop-blur-md shadow-xl overflow-hidden">
        {loading ? (
          <div className="p-16 text-center text-slate-400">
            <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            Đang tải sổ cái kiểm toán...
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="p-16 text-center text-slate-400 text-base">
            Không có sự kiện kiểm toán nào phù hợp.
          </div>
        ) : (
          <div className="divide-y divide-slate-800/70 max-h-[700px] overflow-y-auto">
            {filteredEvents.map((ev, i) => {
              const style = typeStyles[ev.event_type] || {
                label: ev.event_type,
                color: "bg-slate-800 text-slate-300 border-slate-700",
              };

              return (
                <div key={i} className="p-5 hover:bg-slate-800/30 transition-colors space-y-2">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-3">
                      <span
                        className={`px-3 py-1 rounded-lg text-xs font-black uppercase tracking-wider border ${style.color}`}
                      >
                        {ev.event_type} • {style.label}
                      </span>
                      <span className="text-sm font-bold text-white">
                        Tác nhân: <span className="text-cyan-300 font-mono">{ev.actor}</span>
                      </span>
                      {ev.target_id && (
                        <span className="text-xs text-slate-400 font-mono">
                          Mục tiêu: {ev.target_id.slice(0, 8)}...
                        </span>
                      )}
                    </div>

                    <span className="text-xs text-slate-400 font-mono">
                      {ev.timestamp}
                    </span>
                  </div>

                  {ev.details && Object.keys(ev.details).length > 0 && (
                    <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 font-mono text-xs text-slate-300 overflow-x-auto">
                      {JSON.stringify(ev.details, null, 2)}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
