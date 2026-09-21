"use client";

import { useState, useRef } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    setResult(null);

    const form = new FormData();
    form.append("file", file);

    try {
      const res = await fetch(`${API}/api/datasets`, {
        method: "POST",
        body: form,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Upload failed");
      setResult(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
          Upload Dataset
        </h1>
        <p className="text-gray-400 mt-1">
          Upload CSV, XLSX, or Parquet files for analysis
        </p>
      </div>

      {/* Drop Zone */}
      <div
        className={`border-2 border-dashed rounded-xl p-12 text-center transition-all cursor-pointer ${
          dragging
            ? "border-emerald-400 bg-emerald-400/5"
            : "border-gray-700 hover:border-gray-600 bg-gray-900/50"
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const f = e.dataTransfer.files[0];
          if (f) setFile(f);
        }}
        onClick={() => fileRef.current?.click()}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".csv,.tsv,.xlsx,.xls,.parquet,.pq"
          className="hidden"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        <div className="text-5xl mb-4">📁</div>
        {file ? (
          <div>
            <p className="text-lg font-medium text-emerald-400">
              {file.name}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              {(file.size / 1024).toFixed(1)} KB • Click to change
            </p>
          </div>
        ) : (
          <div>
            <p className="text-lg text-gray-400">
              Drop your file here or click to browse
            </p>
            <p className="text-sm text-gray-600 mt-1">
              Supports CSV, TSV, XLSX, Parquet
            </p>
          </div>
        )}
      </div>

      {/* Upload Button */}
      {file && (
        <button
          onClick={handleUpload}
          disabled={uploading}
          className="mt-4 px-6 py-3 bg-gradient-to-r from-emerald-500 to-cyan-500 hover:from-emerald-400 hover:to-cyan-400 text-white font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {uploading ? (
            <span className="flex items-center gap-2">
              <svg
                className="animate-spin w-4 h-4"
                viewBox="0 0 24 24"
              >
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
              Analyzing...
            </span>
          ) : (
            "Upload & Analyze"
          )}
        </button>
      )}

      {error && (
        <div className="mt-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="mt-8 space-y-6">
          {/* Summary */}
          <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-6">
            <h2 className="text-xl font-bold mb-4">Analysis Results</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MiniStat
                label="Rows"
                value={result.summary?.total_rows}
              />
              <MiniStat
                label="Columns"
                value={result.summary?.total_columns}
              />
              <MiniStat
                label="Evidence"
                value={result.summary?.total_evidence}
              />
              <MiniStat
                label="Time"
                value={`${result.summary?.elapsed_seconds}s`}
              />
            </div>
          </div>

          {/* Decisions */}
          <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-6">
            <h2 className="text-xl font-bold mb-4">Decisions</h2>
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-center">
                <p className="text-3xl font-bold text-emerald-400">
                  {result.summary?.auto_count}
                </p>
                <p className="text-sm text-emerald-300/70">AUTO</p>
              </div>
              <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/30 text-center">
                <p className="text-3xl font-bold text-amber-400">
                  {result.summary?.escalate_count}
                </p>
                <p className="text-sm text-amber-300/70">ESCALATE</p>
              </div>
              <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-center">
                <p className="text-3xl font-bold text-red-400">
                  {result.summary?.block_count}
                </p>
                <p className="text-sm text-red-300/70">BLOCK</p>
              </div>
            </div>
          </div>

          {/* Column Profiles */}
          {result.profile?.columns && (
            <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-6">
              <h2 className="text-xl font-bold mb-4">Column Profiles</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-800 text-gray-400">
                      <th className="text-left py-2 px-3">Column</th>
                      <th className="text-left py-2 px-3">Type</th>
                      <th className="text-left py-2 px-3">Semantic</th>
                      <th className="text-right py-2 px-3">Missing%</th>
                      <th className="text-right py-2 px-3">Unique%</th>
                      <th className="text-right py-2 px-3">
                        Cardinality
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.profile.columns.map(
                      (col: any, i: number) => (
                        <tr
                          key={i}
                          className="border-b border-gray-800/50 hover:bg-gray-800/30"
                        >
                          <td className="py-2 px-3 font-medium">
                            {col.column_name}
                          </td>
                          <td className="py-2 px-3 text-gray-400">
                            {col.observed_type}
                          </td>
                          <td className="py-2 px-3">
                            {col.semantic_type ? (
                              <span className="px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 text-xs">
                                {col.semantic_type}
                              </span>
                            ) : (
                              <span className="text-gray-600">—</span>
                            )}
                          </td>
                          <td className="py-2 px-3 text-right">
                            <span
                              className={
                                col.missing_rate > 0.1
                                  ? "text-red-400"
                                  : "text-gray-400"
                              }
                            >
                              {(col.missing_rate * 100).toFixed(1)}%
                            </span>
                          </td>
                          <td className="py-2 px-3 text-right text-gray-400">
                            {(col.unique_rate * 100).toFixed(1)}%
                          </td>
                          <td className="py-2 px-3 text-right text-gray-400">
                            {col.cardinality}
                          </td>
                        </tr>
                      )
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function MiniStat({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="text-center">
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-xs text-gray-500">{label}</p>
    </div>
  );
}
