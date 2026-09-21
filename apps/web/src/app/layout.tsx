import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "DataGuard AI — Trợ lý Giám sát & Quản trị Chất lượng Dữ liệu Doanh nghiệp",
  description:
    "Hệ thống tác tử AI kiểm soát chất lượng dữ liệu với cơ chế điều phối chuyển tiếp (Escalation Referee), hợp nhất bằng chứng Dempster-Shafer và cổng tự chủ trách nhiệm giải trình.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi" className={`${inter.variable} dark`}>
      <body className="min-h-screen bg-[#090D16] text-slate-100 font-[family-name:var(--font-inter)] antialiased selection:bg-emerald-500 selection:text-white">
        <div className="flex min-h-screen">
          {/* Sidebar */}
          <aside className="w-72 bg-[#0E1322]/90 border-r border-slate-800/80 p-5 flex flex-col justify-between fixed h-screen z-30 backdrop-blur-xl shadow-2xl">
            <div>
              {/* Brand Header */}
              <div className="mb-8 pb-5 border-b border-slate-800/80">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 via-teal-400 to-cyan-400 flex items-center justify-center text-xl font-black text-slate-950 shadow-lg shadow-emerald-500/20">
                    🛡️
                  </div>
                  <div>
                    <h1 className="text-2xl font-black tracking-tight bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-300 bg-clip-text text-transparent">
                      DataGuard AI
                    </h1>
                    <p className="text-xs font-semibold text-slate-400 tracking-wide uppercase mt-0.5">
                      The Escalation Referee
                    </p>
                  </div>
                </div>
                <div className="mt-3 flex items-center justify-between px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    Hệ thống: Sẵn sàng
                  </span>
                  <span className="text-[10px] text-emerald-300/70 font-mono">v2.0 PRO</span>
                </div>
              </div>

              {/* Navigation */}
              <nav className="flex flex-col gap-1.5">
                <a
                  href="/"
                  className="px-3.5 py-3 rounded-xl hover:bg-slate-800/70 text-slate-300 hover:text-white transition-all flex items-center gap-3 text-sm font-medium border border-transparent hover:border-slate-700/60 group"
                >
                  <span className="text-lg group-hover:scale-110 transition-transform">📊</span>
                  <span>Tổng quan (Dashboard)</span>
                </a>
                <a
                  href="/upload"
                  className="px-3.5 py-3 rounded-xl hover:bg-slate-800/70 text-slate-300 hover:text-white transition-all flex items-center gap-3 text-sm font-medium border border-transparent hover:border-slate-700/60 group"
                >
                  <span className="text-lg group-hover:scale-110 transition-transform">📁</span>
                  <span>Tải tệp & Trợ lý AI (Upload)</span>
                </a>
                <a
                  href="/datasets"
                  className="px-3.5 py-3 rounded-xl hover:bg-slate-800/70 text-slate-300 hover:text-white transition-all flex items-center gap-3 text-sm font-medium border border-transparent hover:border-slate-700/60 group"
                >
                  <span className="text-lg group-hover:scale-110 transition-transform">🗄️</span>
                  <span>Bộ Dữ liệu & Báo cáo (Datasets)</span>
                </a>
                <a
                  href="/reviews"
                  className="px-3.5 py-3 rounded-xl hover:bg-slate-800/70 text-slate-300 hover:text-white transition-all flex items-center gap-3 text-sm font-medium border border-transparent hover:border-slate-700/60 group"
                >
                  <span className="text-lg group-hover:scale-110 transition-transform">⚖️</span>
                  <span>Hàng đợi Phê duyệt (Review Queue)</span>
                </a>
                <a
                  href="/audit"
                  className="px-3.5 py-3 rounded-xl hover:bg-slate-800/70 text-slate-300 hover:text-white transition-all flex items-center gap-3 text-sm font-medium border border-transparent hover:border-slate-700/60 group"
                >
                  <span className="text-lg group-hover:scale-110 transition-transform">📜</span>
                  <span>Sổ cái Kiểm toán (Audit Trail)</span>
                </a>
                <a
                  href="/verify"
                  className="px-3.5 py-3 rounded-xl bg-gradient-to-r from-emerald-500/10 to-cyan-500/10 hover:from-emerald-500/20 hover:to-cyan-500/20 text-emerald-300 hover:text-white transition-all flex items-center justify-between text-sm font-semibold border border-emerald-500/30 group mt-2"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-lg group-hover:scale-110 transition-transform">🚀</span>
                    <span>Kiểm thử Cuộc thi (Verify)</span>
                  </div>
                  <span className="px-1.5 py-0.5 rounded text-[11px] bg-emerald-500/20 text-emerald-300 font-mono font-bold">
                    5/5
                  </span>
                </a>
              </nav>
            </div>

            {/* Bottom Engine Specs */}
            <div className="pt-4 border-t border-slate-800/80 space-y-2">
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400 space-y-1">
                <div className="flex items-center justify-between font-semibold text-slate-300">
                  <span>⚡ Polars SIMD Engine</span>
                  <span className="text-emerald-400">Rust Core</span>
                </div>
                <p className="text-[11px] text-slate-500">
                  Xử lý luồng streaming 1M+ dòng trong ~2 giây (Zero-copy Arrow).
                </p>
              </div>
              <p className="text-[11px] text-slate-500 text-center italic">
                "Uncertainty is a routing signal"
              </p>
            </div>
          </aside>

          {/* Main Content Area */}
          <main className="ml-72 flex-1 p-8 lg:p-10 max-w-[1600px]">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
