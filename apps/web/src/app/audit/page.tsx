"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AuditPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/audit?limit=50`)
      .then((r) => r.json())
      .then((d) => {
        setEvents(d.events || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const typeColors: Record<string, string> = {
    UPLOAD: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    PROFILE: "bg-purple-500/20 text-purple-400 border-purple-500/30",
    DETECT: "bg-indigo-500/20 text-indigo-400 border-indigo-500/30",
    AUTO: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    ESCALATE: "bg-amber-500/20 text-amber-400 border-amber-500/30",
    BLOCK: "bg-red-500/20 text-red-400 border-red-500/30",
    REVIEW: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
    DELETE: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
          Audit Trail
        </h1>
        <p className="text-gray-400 mt-1">
          Complete decision history — who did what, when, and why
        </p>
      </div>

      <div className="bg-gray-900/50 rounded-xl border border-gray-800">
        {loading ? (
          <div className="p-8 text-center text-gray-500">Loading...</div>
        ) : events.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No audit events yet
          </div>
        ) : (
          <div className="divide-y divide-gray-800">
            {events.map((ev, i) => (
              <div
                key={i}
                className="p-4 hover:bg-gray-800/30 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium border ${
                      typeColors[ev.event_type] ||
                      "bg-gray-500/20 text-gray-400 border-gray-500/30"
                    }`}
                  >
                    {ev.event_type}
                  </span>
                  <span className="text-sm text-gray-400">
                    {ev.actor}
                  </span>
                  <span className="text-xs text-gray-600 ml-auto">
                    {ev.timestamp}
                  </span>
                </div>
                {ev.details && Object.keys(ev.details).length > 0 && (
                  <div className="mt-2 text-xs text-gray-500 font-mono">
                    {JSON.stringify(ev.details).slice(0, 200)}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
