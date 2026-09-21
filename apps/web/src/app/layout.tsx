import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "DataGuard — Risk-Aware Data Quality",
  description:
    "An evidence-driven AI data-operations worker that knows when it can act, when it must ask, and when it must refuse.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} dark`}>
      <body className="min-h-screen bg-gray-950 text-gray-100 font-[family-name:var(--font-inter)]">
        <div className="flex min-h-screen">
          {/* Sidebar */}
          <aside className="w-64 bg-gray-900/80 border-r border-gray-800 p-4 flex flex-col gap-2 fixed h-screen">
            <div className="mb-6">
              <h1 className="text-xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
                DataGuard
              </h1>
              <p className="text-xs text-gray-500 mt-1">
                Risk-Aware Data Quality
              </p>
            </div>
            <nav className="flex flex-col gap-1">
              <a
                href="/"
                className="px-3 py-2 rounded-lg hover:bg-gray-800 text-sm text-gray-300 hover:text-white transition-colors flex items-center gap-2"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                  />
                </svg>
                Dashboard
              </a>
              <a
                href="/datasets"
                className="px-3 py-2 rounded-lg hover:bg-gray-800 text-sm text-gray-300 hover:text-white transition-colors flex items-center gap-2"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"
                  />
                </svg>
                Datasets
              </a>
              <a
                href="/upload"
                className="px-3 py-2 rounded-lg hover:bg-gray-800 text-sm text-gray-300 hover:text-white transition-colors flex items-center gap-2"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
                  />
                </svg>
                Upload
              </a>
              <a
                href="/reviews"
                className="px-3 py-2 rounded-lg hover:bg-gray-800 text-sm text-gray-300 hover:text-white transition-colors flex items-center gap-2"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                  />
                </svg>
                Reviews
              </a>
              <a
                href="/audit"
                className="px-3 py-2 rounded-lg hover:bg-gray-800 text-sm text-gray-300 hover:text-white transition-colors flex items-center gap-2"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                Audit Trail
              </a>
              <a
                href="/verify"
                className="px-3 py-2 rounded-lg hover:bg-gray-800 text-sm text-gray-300 hover:text-white transition-colors flex items-center gap-2"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                Verify
              </a>
            </nav>
            <div className="mt-auto pt-4 border-t border-gray-800">
              <p className="text-xs text-gray-600 italic">
                "Uncertainty is a routing signal"
              </p>
            </div>
          </aside>

          {/* Main content */}
          <main className="ml-64 flex-1 p-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
