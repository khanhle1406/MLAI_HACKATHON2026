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
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
          Verify Harness
        </h1>
        <p className="text-gray-400 mt-1">
          One-click competition verification — 5 test cases
        </p>
      </div>

      {/* Run Button */}
      <button
        onClick={runVerify}
        disabled={loading}
        className="px-8 py-4 bg-gradient-to-r from-emerald-500 to-cyan-500 hover:from-emerald-400 hover:to-cyan-400 text-white font-bold rounded-xl text-lg transition-all disabled:opacity-50 shadow-lg shadow-emerald-500/20"
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24">
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
                fill="none"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            Running Verify...
          </span>
        ) : (
          "🚀 Run All Tests"
        )}
      </button>

      {/* Results */}
      {results && (
        <div className="mt-8 space-y-6">
          {/* Score Summary */}
          <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">Results</h2>
              <span className="text-sm text-gray-500">
                {results.timestamp}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
                <p className="text-sm text-gray-400">Routine Automation</p>
                <p className="text-2xl font-bold text-emerald-400">
                  {results.routine_automation}
                </p>
              </div>
              <div className="text-center p-4 rounded-lg bg-amber-500/10 border border-amber-500/30">
                <p className="text-sm text-gray-400">Escalation</p>
                <p className="text-2xl font-bold text-amber-400">
                  {results.escalation}
                </p>
              </div>
              <div
                className={`text-center p-4 rounded-lg border ${
                  results.overall_pass
                    ? "bg-emerald-500/10 border-emerald-500/30"
                    : "bg-red-500/10 border-red-500/30"
                }`}
              >
                <p className="text-sm text-gray-400">Total</p>
                <p
                  className={`text-2xl font-bold ${
                    results.overall_pass
                      ? "text-emerald-400"
                      : "text-red-400"
                  }`}
                >
                  {results.total}
                </p>
              </div>
            </div>
          </div>

          {/* Test Cases */}
          <div className="bg-gray-900/50 rounded-xl border border-gray-800">
            <div className="p-4 border-b border-gray-800">
              <h2 className="text-lg font-semibold">Test Cases</h2>
            </div>
            <div className="divide-y divide-gray-800">
              {results.cases?.map((c: any) => (
                <div
                  key={c.case_id}
                  className="p-4 flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                        c.passed
                          ? "bg-emerald-500/20 text-emerald-400"
                          : "bg-red-500/20 text-red-400"
                      }`}
                    >
                      {c.passed ? "✓" : "✗"}
                    </span>
                    <div>
                      <p className="font-medium">
                        {c.case_id}: {c.description}
                      </p>
                      <p className="text-sm text-gray-500">
                        Expected: {c.expected_decision} • Actual:{" "}
                        {c.actual_decision || "—"} •{" "}
                        {c.duration_seconds}s
                      </p>
                    </div>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-medium ${
                      c.passed
                        ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                        : "bg-red-500/20 text-red-400 border border-red-500/30"
                    }`}
                  >
                    {c.passed ? "PASS" : "FAIL"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
