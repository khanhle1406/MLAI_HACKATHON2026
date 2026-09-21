"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Dataset {
  id: string;
  filename: string;
  status: string;
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

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
          Dashboard
        </h1>
        <p className="text-gray-400 mt-1">
          Data quality operations overview
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          title="Datasets"
          value={datasets.length}
          icon="📊"
          color="from-blue-500 to-blue-600"
        />
        <StatCard
          title="AUTO Fixes"
          value={totalAuto}
          icon="⚡"
          color="from-emerald-500 to-emerald-600"
          subtitle="Safe autonomous actions"
        />
        <StatCard
          title="Escalated"
          value={totalEsc}
          icon="🔔"
          color="from-amber-500 to-amber-600"
          subtitle="Needs human review"
        />
        <StatCard
          title="Blocked"
          value={totalBlock}
          icon="🛑"
          color="from-red-500 to-red-600"
          subtitle="Security/unsupported"
        />
      </div>

      {/* Automation Rate */}
      {totalDecisions > 0 && (
        <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-6 mb-8">
          <h2 className="text-lg font-semibold mb-4">Automation Rate</h2>
          <div className="flex items-center gap-4">
            <div className="flex-1 bg-gray-800 rounded-full h-4 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 rounded-full transition-all duration-500"
                style={{
                  width: `${(totalAuto / totalDecisions) * 100}%`,
                }}
              />
            </div>
            <span className="text-2xl font-bold text-emerald-400">
              {((totalAuto / totalDecisions) * 100).toFixed(0)}%
            </span>
          </div>
          <div className="flex gap-6 mt-3 text-sm text-gray-400">
            <span>
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 mr-1" />
              AUTO: {totalAuto}
            </span>
            <span>
              <span className="inline-block w-2 h-2 rounded-full bg-amber-500 mr-1" />
              ESCALATE: {totalEsc}
            </span>
            <span>
              <span className="inline-block w-2 h-2 rounded-full bg-red-500 mr-1" />
              BLOCK: {totalBlock}
            </span>
          </div>
        </div>
      )}

      {/* Dataset List */}
      <div className="bg-gray-900/50 rounded-xl border border-gray-800">
        <div className="p-4 border-b border-gray-800">
          <h2 className="text-lg font-semibold">Recent Datasets</h2>
        </div>
        {loading ? (
          <div className="p-8 text-center text-gray-500">Loading...</div>
        ) : datasets.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <p className="text-lg mb-2">No datasets yet</p>
            <a
              href="/upload"
              className="text-emerald-400 hover:text-emerald-300"
            >
              Upload your first dataset →
            </a>
          </div>
        ) : (
          <div className="divide-y divide-gray-800">
            {datasets.map((ds) => (
              <div
                key={ds.id}
                className="p-4 hover:bg-gray-800/50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium">{ds.filename}</h3>
                    <p className="text-sm text-gray-500">
                      {ds.summary?.total_rows} rows ×{" "}
                      {ds.summary?.total_columns} cols •{" "}
                      {ds.summary?.elapsed_seconds}s
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {(ds.summary?.auto_count ?? 0) > 0 && (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                        AUTO: {ds.summary?.auto_count}
                      </span>
                    )}
                    {(ds.summary?.escalate_count ?? 0) > 0 && (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-amber-500/20 text-amber-400 border border-amber-500/30">
                        ESC: {ds.summary?.escalate_count}
                      </span>
                    )}
                    {(ds.summary?.block_count ?? 0) > 0 && (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-red-500/20 text-red-400 border border-red-500/30">
                        BLOCK: {ds.summary?.block_count}
                      </span>
                    )}
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs ${
                        ds.status === "COMPLETED"
                          ? "bg-emerald-500/20 text-emerald-400"
                          : "bg-gray-500/20 text-gray-400"
                      }`}
                    >
                      {ds.status}
                    </span>
                  </div>
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
  icon,
  color,
  subtitle,
}: {
  title: string;
  value: number;
  icon: string;
  color: string;
  subtitle?: string;
}) {
  return (
    <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-5 hover:border-gray-700 transition-colors">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-400">{title}</span>
        <span className="text-2xl">{icon}</span>
      </div>
      <p
        className={`text-3xl font-bold bg-gradient-to-r ${color} bg-clip-text text-transparent`}
      >
        {value}
      </p>
      {subtitle && (
        <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
      )}
    </div>
  );
}
