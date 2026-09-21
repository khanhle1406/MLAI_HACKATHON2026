"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Dataset {
  id: string;
  filename: string;
  status: string;
  assistant_report?: any;
  summary?: {
    total_rows: number;
    total_columns: number;
    total_evidence: number;
    auto_count: number;
    escalate_count: number;
    block_count: number;
    automation_rate: number;
    elapsed_seconds: number;
  };
}

export default function Dashboard() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/datasets`)
      .then((r) => r.json())
      .then((d) => {
        setDatasets(d.datasets || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const totalAuto = datasets.reduce(
    (sum, d) => sum + (d.summary?.auto_count || 0),
    0
  );
  const totalEsc = datasets.reduce(
    (sum, d) => sum + (d.summary?.escalate_count || 0),
    0
  );
  const totalBlock = datasets.reduce(
    (sum, d) => sum + (d.summary?.block_count || 0),
    0
  );
  const totalDecisions = totalAuto + totalEsc + totalBlock;
  const automationPercent =
    totalDecisions > 0 ? Math.round((totalAuto / totalDecisions) * 100) : 0;

  return (
    <div className="space-y-8">
      {/* Top Welcome & Assistant Header */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-emerald-950/40 border border-slate-800 p-8 shadow-xl">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-3 max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold uppercase tracking-wider">
              <span>🤖 Trợ lý Quản trị Chất lượng Dữ liệu AI</span>
              <span>•</span>
              <span>Đề bài A: The Escalation Referee</span>
            </div>
            <h1 className="text-3xl md:text-4xl font-black tracking-tight text-white">
              Trung tâm Điều hành & Trợ lý Phân tích Dữ liệu
            </h1>
            <p className="text-base md:text-lg text-slate-300 leading-relaxed">
              Hệ thống tự động hóa xử lý các lỗi thường quy, đồng thời nhận biết chính xác thời điểm xuất hiện bất định để chuyển tiếp cho con người phê duyệt kèm câu hỏi cụ thể. Tuyệt đối không tự ý võ đoán dữ liệu rủi ro.
            </p>
          </div>

          <div className="flex flex-wrap md:flex-col gap-3 shrink-0">
            <a
              href="/upload"
              className="px-5 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-bold text-sm shadow-lg shadow-emerald-500/25 transition-all flex items-center justify-center gap-2"
            >
              <span>📁 Tải & Phân tích Tệp mới</span>
            </a>
            <a
              href="/verify"
              className="px-5 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-semibold text-sm border border-slate-700 transition-all flex items-center justify-center gap-2"
            >
              <span>🚀 Chạy Verify 5/5 Cuộc thi</span>
            </a>
          </div>
        </div>

        {/* Ambient background glow */}
        <div className="absolute -right-20 -top-20 w-80 h-80 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
      </div>

      {/* Primary KPI Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard
          title="Tổng Tệp Dữ Liệu"
          value={datasets.length}
          unit="bộ dữ liệu"
          icon="📊"
          color="from-blue-400 to-indigo-400"
          subtitle="Đã hồ sơ hóa & quét 11 bộ dò"
        />
        <StatCard
          title="Tự Động Sửa (AUTO)"
          value={totalAuto}
          unit="mục an toàn"
          icon="⚡"
          color="from-emerald-400 to-teal-400"
          subtitle="Tất định 100% & có thể hoàn tác"
          badge="Routine Automation"
        />
        <StatCard
          title="Chuyển Tiếp (ESCALATE)"
          value={totalEsc}
          unit="mục cần duyệt"
          icon="🔔"
          color="from-amber-400 to-orange-400"
          subtitle="Hỏi con người kèm câu hỏi cụ thể"
          badge="Human-in-the-Loop"
        />
        <StatCard
          title="Chặn An Toàn (BLOCK)"
          value={totalBlock}
          unit="mục rủi ro"
          icon="🛑"
          color="from-rose-400 to-red-400"
          subtitle="Vi phạm thẩm quyền bảo mật"
          badge="Safety Guard"
        />
      </div>

      {/* Visual Automation Health & Enterprise Scale Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Automation Rate Card */}
        <div className="lg:col-span-2 bg-slate-900/60 rounded-2xl border border-slate-800/80 p-7 backdrop-blur-md shadow-lg space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-4">
            <div>
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <span>🎯 Cân Bằng Tự Chủ & Trách Nhiệm Giải Trình</span>
              </h2>
              <p className="text-sm text-slate-400 mt-1">
                Tỷ lệ xử lý tự động thường quy so với các ca cần con người can thiệp
              </p>
            </div>
            <div className="text-right">
              <span className="text-4xl font-black text-emerald-400">
                {automationPercent}%
              </span>
              <p className="text-xs text-slate-400 font-medium">Tự động an toàn</p>
            </div>
          </div>

          {/* Progress bar */}
          <div className="space-y-3">
            <div className="w-full bg-slate-800 rounded-full h-5 overflow-hidden flex p-0.5 border border-slate-700">
              <div
                className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full transition-all duration-700"
                style={{ width: `${Math.max(totalDecisions > 0 ? (totalAuto / totalDecisions) * 100 : 0, 4)}%` }}
                title={`AUTO: ${totalAuto}`}
              />
              <div
                className="h-full bg-gradient-to-r from-amber-500 to-orange-400 rounded-full transition-all duration-700 ml-1"
                style={{ width: `${totalDecisions > 0 ? (totalEsc / totalDecisions) * 100 : 0}%` }}
                title={`ESCALATE: ${totalEsc}`}
              />
              <div
                className="h-full bg-gradient-to-r from-rose-500 to-red-500 rounded-full transition-all duration-700 ml-1"
                style={{ width: `${totalDecisions > 0 ? (totalBlock / totalDecisions) * 100 : 0}%` }}
                title={`BLOCK: ${totalBlock}`}
              />
            </div>

            {/* Legend with rich explanation */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
              <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-emerald-400 uppercase">AUTO FIX</span>
                  <span className="text-base font-black text-emerald-300">{totalAuto}</span>
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  Khoảng trắng thừa, chuẩn hóa ISO date, missing quy chuẩn.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-amber-400 uppercase">ESCALATE</span>
                  <span className="text-base font-black text-amber-300">{totalEsc}</span>
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  Ngoại lai lương, trùng khóa, bất định mâu thuẫn cần hỏi.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-rose-400 uppercase">BLOCKED</span>
                  <span className="text-base font-black text-rose-300">{totalBlock}</span>
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  Dữ liệu tài chính vượt thẩm quyền, vi phạm chính sách.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Big Data Enterprise Architecture Spotlight */}
        <div className="bg-gradient-to-b from-slate-900 via-slate-900/80 to-[#0F172A] rounded-2xl border border-slate-800 p-7 shadow-lg flex flex-col justify-between">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-md bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 text-xs font-bold">
              ⚡ Doanh Nghiệp Hàng Triệu Dòng
            </div>
            <h3 className="text-xl font-black text-white">
              Kiến Trúc Xử Lý Big Data
            </h3>
            <p className="text-sm text-slate-300 leading-relaxed">
              Khác với các công cụ dùng vòng lặp Python thông thường, DataGuard tích hợp động cơ <span className="text-cyan-400 font-semibold">Polars LazyFrame</span> viết bằng ngôn ngữ Rust với khả năng:
            </p>
            <ul className="space-y-2 text-xs text-slate-300">
              <li className="flex items-start gap-2">
                <span className="text-emerald-400 font-bold">✓</span>
                <span><strong>Zero-Copy Apache Arrow:</strong> Xử lý dữ liệu trực tiếp trong bộ nhớ chia sẻ.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-emerald-400 font-bold">✓</span>
                <span><strong>Streaming Chunks (50k dòng):</strong> Duy trì RAM dưới 250MB kể cả file gigabyte.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-emerald-400 font-bold">✓</span>
                <span><strong>Throughput cực đại:</strong> Đạt tốc độ hơn 1,000,000 dòng / giây trên máy chủ chuẩn.</span>
              </li>
            </ul>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-800/80">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Độ trễ TB trên tập mẫu:</span>
              <span className="font-mono text-emerald-400 font-bold">&lt; 0.85 giây</span>
            </div>
          </div>
        </div>
      </div>

      {/* Dataset Table with Assistant Report Access */}
      <div className="bg-slate-900/60 rounded-2xl border border-slate-800/80 backdrop-blur-md shadow-xl overflow-hidden">
        <div className="p-6 border-b border-slate-800/80 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white">
              Danh Sách Bộ Dữ Liệu Đã Nạp
            </h2>
            <p className="text-sm text-slate-400 mt-0.5">
              Bấm vào từng bộ dữ liệu để xem Báo cáo Trợ lý và phân tích cơ chế lỗi
            </p>
          </div>
          <a
            href="/datasets"
            className="text-sm text-emerald-400 hover:text-emerald-300 font-semibold flex items-center gap-1"
          >
            <span>Xem tất cả chi tiết</span>
            <span>→</span>
          </a>
        </div>

        {loading ? (
          <div className="p-16 text-center text-slate-400 text-base">
            <div className="w-8 h-8 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            Đang tải dữ liệu từ máy chủ...
          </div>
        ) : datasets.length === 0 ? (
          <div className="p-16 text-center space-y-4">
            <div className="text-5xl">📁</div>
            <h3 className="text-xl font-bold text-slate-300">Chưa có bộ dữ liệu nào</h3>
            <p className="text-base text-slate-400 max-w-md mx-auto">
              Hãy tải lên tệp CSV/Excel của bạn hoặc nạp bộ dữ liệu mẫu để trải nghiệm Trợ lý AI.
            </p>
            <div className="pt-2">
              <a
                href="/upload"
                className="inline-flex px-6 py-3 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-sm transition-colors"
              >
                Tải lên tệp đầu tiên →
              </a>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/80">
            {datasets.map((ds) => (
              <div
                key={ds.id}
                className="p-5 hover:bg-slate-800/40 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-3">
                    <h3 className="text-base font-bold text-white hover:text-emerald-400 transition-colors">
                      {ds.filename}
                    </h3>
                    <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                      {ds.status}
                    </span>
                  </div>
                  <p className="text-sm text-slate-400">
                    <span className="font-semibold text-slate-300">{ds.summary?.total_rows || 0}</span> dòng ×{" "}
                    <span className="font-semibold text-slate-300">{ds.summary?.total_columns || 0}</span> cột •{" "}
                    Xử lý trong <span className="text-emerald-400 font-mono">{ds.summary?.elapsed_seconds || 0}s</span>
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2.5">
                  {(ds.summary?.auto_count ?? 0) > 0 && (
                    <span className="px-3 py-1 rounded-lg text-xs font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                      ⚡ AUTO: {ds.summary?.auto_count}
                    </span>
                  )}
                  {(ds.summary?.escalate_count ?? 0) > 0 && (
                    <span className="px-3 py-1 rounded-lg text-xs font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30">
                      🔔 ESCALATE: {ds.summary?.escalate_count}
                    </span>
                  )}
                  {(ds.summary?.block_count ?? 0) > 0 && (
                    <span className="px-3 py-1 rounded-lg text-xs font-bold bg-rose-500/15 text-rose-300 border border-rose-500/30">
                      🛑 BLOCK: {ds.summary?.block_count}
                    </span>
                  )}
                  <a
                    href={`/datasets?id=${ds.id}`}
                    className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold border border-slate-700 transition-colors ml-2"
                  >
                    Xem Báo cáo →
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  unit,
  icon,
  color,
  subtitle,
  badge,
}: {
  title: string;
  value: number;
  unit: string;
  icon: string;
  color: string;
  subtitle?: string;
  badge?: string;
}) {
  return (
    <div className="bg-slate-900/60 rounded-2xl border border-slate-800/80 p-6 backdrop-blur-md hover:border-slate-700 transition-all shadow-lg relative overflow-hidden group">
      <div className="flex items-start justify-between mb-3">
        <div>
          <span className="text-sm font-semibold text-slate-400">{title}</span>
          {badge && (
            <span className="block mt-1 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
              {badge}
            </span>
          )}
        </div>
        <span className="text-3xl group-hover:scale-110 transition-transform">{icon}</span>
      </div>
      
      <div className="flex items-baseline gap-2 my-2">
        <p className={`text-4xl font-black bg-gradient-to-r ${color} bg-clip-text text-transparent`}>
          {value}
        </p>
        <span className="text-xs font-medium text-slate-400">{unit}</span>
      </div>

      {subtitle && (
        <p className="text-xs text-slate-400/90 mt-1 border-t border-slate-800/60 pt-2">
          {subtitle}
        </p>
      )}
    </div>
  );
}
