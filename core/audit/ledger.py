"""Audit ledger — immutable event log for DataGuard.

Records every significant action in the system for traceability.
Board A requirement: "Audit trail truy xuất được — ai làm gì, khi nào, dữ liệu nào, lý do."

INVARIANT: Failed audit write BLOCKS commit (I8).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

# In-memory audit store (will be replaced with DB in production)
_audit_store: list[dict[str, Any]] = []


class AuditLedger:
    """Immutable audit event recorder."""

    def __init__(self):
        self._events: list[dict[str, Any]] = _audit_store

    def record(
        self,
        event_type: str,
        actor: str,
        dataset_id: str | None = None,
        decision_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> str:
        """Record an audit event.

        Args:
            event_type: Type of event (UPLOAD, PROFILE, DETECT, etc.)
            actor: Who performed the action (system, user:xxx, model:gpt-4o)
            dataset_id: Related dataset ID.
            decision_id: Related decision ID.
            details: Additional event details.

        Returns:
            Event ID.

        Raises:
            RuntimeError: If audit write fails (blocks commit per I8).
        """
        event_id = str(uuid4())
        event = {
            "id": event_id,
            "event_type": event_type,
            "actor": actor,
            "dataset_id": dataset_id,
            "decision_id": decision_id,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            self._events.append(event)
            logger.info(f"AUDIT: {event_type} by {actor} | dataset={dataset_id}")
            return event_id
        except Exception as e:
            # INVARIANT I8: Failed audit persistence BLOCKS commit
            raise RuntimeError(f"Audit write failed — commit blocked: {e}") from e

    def query(
        self,
        dataset_id: str | None = None,
        event_type: str | None = None,
        actor: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Query audit events with optional filters."""
        results = self._events

        if dataset_id:
            results = [e for e in results if e.get("dataset_id") == dataset_id]
        if event_type:
            results = [e for e in results if e.get("event_type") == event_type]
        if actor:
            results = [e for e in results if e.get("actor") == actor]

        # Sort by timestamp descending (most recent first)
        results = sorted(results, key=lambda e: e.get("timestamp", ""), reverse=True)

        return results[offset: offset + limit]

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        """Get a single audit event by ID."""
        for event in self._events:
            if event["id"] == event_id:
                return event
        return None

    def count(self, dataset_id: str | None = None) -> int:
        """Count audit events."""
        if dataset_id:
            return sum(1 for e in self._events if e.get("dataset_id") == dataset_id)
        return len(self._events)

    def get_timeline(self, dataset_id: str) -> list[dict[str, Any]]:
        """Get ordered timeline of events for a dataset."""
        events = [e for e in self._events if e.get("dataset_id") == dataset_id]
        return sorted(events, key=lambda e: e.get("timestamp", ""))


# Singleton
audit_ledger = AuditLedger()
