"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ReviewsPage() {
  const [reviews, setReviews] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadReviews = () => {
    fetch(`${API}/api/reviews`)
      .then((r) => r.json())
      .then((d) => {
        setReviews(d.queue || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadReviews();
  }, []);

  const handleAction = async (
    decisionId: string,
    action: string
  ) => {
    try {
      await fetch(`${API}/api/reviews/${decisionId}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: action.toUpperCase(),
          reviewer: "user",
          comment: `${action} via UI`,
        }),
      });
      loadReviews();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
          Review Queue
        </h1>
        <p className="text-gray-400 mt-1">
          Items escalated for human review
        </p>
      </div>

      {loading ? (
        <div className="text-center text-gray-500 py-12">Loading...</div>
      ) : reviews.length === 0 ? (
        <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-12 text-center">
          <div className="text-5xl mb-4">✅</div>
          <p className="text-lg text-gray-400">No pending reviews</p>
          <p className="text-sm text-gray-600 mt-1">
            Upload a dataset to generate escalation items
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {reviews.map((r, i) => (
            <div
              key={i}
              className="bg-gray-900/50 rounded-xl border border-gray-800 p-5 hover:border-gray-700 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 text-xs font-medium border border-amber-500/30">
                      {r.uncertainty_type || "UNKNOWN"}
                    </span>
                    <span className="text-sm text-gray-500">
                      Row {r.row_id} • Column: {r.column}
                    </span>
                  </div>
                  <p className="text-sm mb-2">
                    <span className="text-gray-400">Value: </span>
                    <code className="px-2 py-0.5 rounded bg-gray-800 text-gray-300">
                      {r.old_value}
                    </code>
                  </p>
                  {r.question && (
                    <div className="bg-gray-800/50 rounded-lg p-3 mt-2 text-sm text-gray-300 whitespace-pre-wrap">
                      {r.question.slice(0, 300)}
                    </div>
                  )}
                  <div className="flex gap-4 mt-2 text-xs text-gray-500">
                    <span>
                      Bel(err)={r.belief_error?.toFixed(3)}
                    </span>
                    <span>K={r.conflict_k?.toFixed(3)}</span>
                    <span>
                      Ignorance={r.ignorance?.toFixed(3)}
                    </span>
                  </div>
                </div>
                <div className="flex gap-2 ml-4">
                  {!r.reviewed && (
                    <>
                      <button
                        onClick={() =>
                          handleAction(r.decision_id, "approve")
                        }
                        className="px-3 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-400 text-sm hover:bg-emerald-500/30 border border-emerald-500/30 transition-colors"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() =>
                          handleAction(r.decision_id, "reject")
                        }
                        className="px-3 py-1.5 rounded-lg bg-red-500/20 text-red-400 text-sm hover:bg-red-500/30 border border-red-500/30 transition-colors"
                      >
                        Reject
                      </button>
                    </>
                  )}
                  {r.reviewed && (
                    <span className="px-3 py-1.5 rounded-lg bg-gray-700/50 text-gray-400 text-sm">
                      Reviewed
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
