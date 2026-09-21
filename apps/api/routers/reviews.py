"""Review API routes — Human review queue for escalated decisions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.audit.ledger import audit_ledger

router = APIRouter(prefix="/reviews", tags=["reviews"])

# In-memory review store
_review_queue: list[dict[str, Any]] = []
_reviews: dict[str, dict[str, Any]] = {}


class ReviewSubmission(BaseModel):
    action: str  # APPROVE, EDIT, REJECT
    edited_value: str | None = None
    comment: str | None = None
    reviewer: str = "anonymous"
    confidence: float = 1.0


def add_to_review_queue(decision: dict[str, Any]):
    """Add an escalated decision to the review queue."""
    _review_queue.append(decision)


@router.get("")
async def list_reviews(status: str | None = None):
    """List items in the review queue."""
    from apps.api.routers.datasets import _analysis_results

    queue = []
    for dataset_id, result in _analysis_results.items():
        for d in result.get("decisions", []):
            if d.get("decision") == "ESCALATE":
                reviewed = d.get("decision_id") in _reviews
                if status == "pending" and reviewed:
                    continue
                if status == "reviewed" and not reviewed:
                    continue
                queue.append({
                    **d,
                    "dataset_id": dataset_id,
                    "reviewed": reviewed,
                    "review": _reviews.get(d.get("decision_id")),
                })

    return {
        "queue": queue,
        "total": len(queue),
        "pending": sum(1 for q in queue if not q.get("reviewed")),
        "reviewed": sum(1 for q in queue if q.get("reviewed")),
    }


@router.post("/{decision_id}/approve")
async def approve_decision(decision_id: str, body: ReviewSubmission):
    """Approve an escalated decision."""
    return await _submit_review(decision_id, "APPROVE", body)


@router.post("/{decision_id}/edit")
async def edit_decision(decision_id: str, body: ReviewSubmission):
    """Edit and approve an escalated decision with a new value."""
    if not body.edited_value:
        raise HTTPException(status_code=400, detail="edited_value is required for EDIT action")
    return await _submit_review(decision_id, "EDIT", body)


@router.post("/{decision_id}/reject")
async def reject_decision(decision_id: str, body: ReviewSubmission):
    """Reject an escalated decision."""
    return await _submit_review(decision_id, "REJECT", body)


async def _submit_review(decision_id: str, action: str, body: ReviewSubmission) -> dict:
    """Process a review submission."""
    review = {
        "review_id": f"rv_{decision_id[:8]}",
        "decision_id": decision_id,
        "action": action,
        "edited_value": body.edited_value,
        "comment": body.comment,
        "reviewer": body.reviewer,
        "confidence": body.confidence,
        "timestamp": datetime.utcnow().isoformat(),
    }

    _reviews[decision_id] = review

    # Record in audit
    audit_ledger.record(
        "REVIEW",
        f"user:{body.reviewer}",
        decision_id=decision_id,
        details={"action": action, "comment": body.comment},
    )

    return {
        "status": "success",
        "review": review,
    }
