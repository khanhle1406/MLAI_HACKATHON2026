"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
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

  const loadDetail = async (id: string) => {
    const res = await fetch(`${API}/api/datasets/${id}`);
    const data = await res.json();
    setSelected(data);
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
          Datasets
        </h1>
        <p className="text-gray-400 mt-1">
          View analysis results and evidence for each dataset
        </p>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Dataset List */}
        <div className="col-span-4">
          <div className="bg-gray-900/50 rounded-xl border border-gray-800">
            <div className="p-3 border-b border-gray-800">
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">
                Uploaded Files
              </h2>
            </div>
            {loading ? (
              <div className="p-4 text-gray-500 text-sm">Loading...</div>
            ) : datasets.length === 0 ? (
              <div className="p-4 text-gray-500 text-sm">
                No datasets uploaded yet.{" "}
                <a href="/upload" className="text-emerald-400">
                  Upload one →
                </a>
              </div>
            ) : (
              <div className="divide-y divide-gray-800">
                {datasets.map((ds) => (
                  <button
                    key={ds.id}
                    onClick={() => loadDetail(ds.id)}
                    className={`w-full text-left p-3 hover:bg-gray-800/50 transition-colors ${
                      selected?.id === ds.id ? "bg-gray-800/70 border-l-2 border-emerald-400" : ""
                    }`}
                  >
                    <p className="font-medium text-sm truncate">{ds.filename}</p>
                    <div className="flex gap-2 mt-1">
                      {ds.summary?.auto_count > 0 && (
                        <span className="text-xs text-emerald-400">
                          AUTO:{ds.summary.auto_count}
                        </span>
                      )}
                      {ds.summary?.escalate_count > 0 && (
                        <span className="text-xs text-amber-400">
                          ESC:{ds.summary.escalate_count}
                        </span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Detail View */}
        <div className="col-span-8">
          {!selected ? (
            <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-12 text-center text-gray-500">
              <p className="text-lg">Select a dataset to view details</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Header */}
              <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-5">
                <h2 className="text-xl font-bold">{selected.filename}</h2>
                <div className="flex gap-4 mt-2 text-sm text-gray-400">
                  <span>{selected.profile?.row_count} rows</span>
                  <span>{selected.profile?.column_count} cols</span>
                  <span>SHA256: {selected.profile?.sha256?.slice(0, 12)}...</span>
                </div>
              </div>

              {/* Evidence & Decisions */}
              {selected.decisions && selected.decisions.length > 0 && (
                <div className="bg-gray-900/50 rounded-xl border border-gray-800">
                  <div className="p-4 border-b border-gray-800 flex items-center justify-between">
                    <h3 className="font-semibold">Decisions</h3>
                    <span className="text-xs text-gray-500">{selected.decisions.length} total</span>
                  </div>
                  <div className="divide-y divide-gray-800 max-h-[500px] overflow-y-auto">
                    {selected.decisions.map((d: any, i: number) => (
                      <div key={i} className="p-4 hover:bg-gray-800/30">
                        <div className="flex items-center gap-2 mb-1">
                          <span
                            className={`px-2 py-0.5 rounded text-xs font-medium ${
                              d.decision === "AUTO"
                                ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                                : d.decision === "ESCALATE"
                                ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                                : "bg-red-500/20 text-red-400 border border-red-500/30"
                            }`}
                          >
                            {d.decision}
                          </span>
                          <span className="text-sm text-gray-400">
                            Row {d.row_id} • <span className="font-mono">{d.column}</span>
                          </span>
                          {d.uncertainty_type && (
                            <span className="text-xs text-gray-600">
                              [{d.uncertainty_type}]
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-gray-300">
                          <code className="px-1.5 py-0.5 bg-gray-800 rounded text-xs">
                            {d.old_value || "—"}
                          </code>
                          {d.new_value && (
                            <>
                              <span className="mx-2 text-gray-600">→</span>
                              <code className="px-1.5 py-0.5 bg-emerald-900/30 rounded text-xs text-emerald-300">
                                {d.new_value}
                              </code>
                            </>
                          )}
                        </div>
                        <div className="flex gap-3 mt-1 text-xs text-gray-600">
                          <span>Bel(err)={d.belief_error?.toFixed(3)}</span>
                          <span>K={d.conflict_k?.toFixed(3)}</span>
                          <span>Ign={d.ignorance?.toFixed(3)}</span>
                          <span>Evidence: {d.evidence_count}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Column Profiles */}
              {selected.profile?.columns && (
                <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-5">
                  <h3 className="font-semibold mb-3">Column Profiles</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-800 text-gray-400 text-xs">
                          <th className="text-left py-2 px-2">Column</th>
                          <th className="text-left py-2 px-2">Type</th>
                          <th className="text-left py-2 px-2">Semantic</th>
                          <th className="text-right py-2 px-2">Missing</th>
                          <th className="text-right py-2 px-2">Unique</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selected.profile.columns.map((col: any, i: number) => (
                          <tr key={i} className="border-b border-gray-800/50">
                            <td className="py-1.5 px-2 font-mono text-xs">{col.column_name}</td>
                            <td className="py-1.5 px-2 text-gray-400 text-xs">{col.observed_type}</td>
                            <td className="py-1.5 px-2">
                              {col.semantic_type && (
                                <span className="px-1.5 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded">
                                  {col.semantic_type}
                                </span>
                              )}
                            </td>
                            <td className="py-1.5 px-2 text-right text-xs">
                              {(col.missing_rate * 100).toFixed(0)}%
                            </td>
                            <td className="py-1.5 px-2 text-right text-xs">
                              {(col.unique_rate * 100).toFixed(0)}%
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
