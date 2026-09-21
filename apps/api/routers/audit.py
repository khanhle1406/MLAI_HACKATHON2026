"""Audit API routes — query the immutable audit trail."""

from __future__ import annotations

from fastapi import APIRouter

from core.audit.ledger import audit_ledger

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
async def query_audit(
    dataset_id: str | None = None,
    event_type: str | None = None,
    actor: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    """Query audit events with optional filters.

    Board A requirement: "Audit trail truy xuất được —
    ai làm gì, khi nào, dữ liệu nào, lý do."
    """
    events = audit_ledger.query(
        dataset_id=dataset_id,
        event_type=event_type,
        actor=actor,
        limit=limit,
        offset=offset,
    )

    return {
        "events": events,
        "total": audit_ledger.count(dataset_id),
        "filters": {
            "dataset_id": dataset_id,
            "event_type": event_type,
            "actor": actor,
        },
    }


@router.get("/timeline/{dataset_id}")
async def get_timeline(dataset_id: str):
    """Get ordered timeline of all events for a dataset."""
    timeline = audit_ledger.get_timeline(dataset_id)
    return {
        "dataset_id": dataset_id,
        "timeline": timeline,
        "total_events": len(timeline),
    }


@router.get("/{event_id}")
async def get_audit_event(event_id: str):
    """Get a single audit event by ID."""
    event = audit_ledger.get_event(event_id)
    if not event:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Audit event not found")
    return event
