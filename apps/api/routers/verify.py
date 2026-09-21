"""Verify API route — One-click competition verify harness.

Board A requirement: "One-click Verify, in bảng kết quả kèm timestamp"
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from core.evidence.schema import Decision, VerifyResult
from core.orchestrator.pipeline import pipeline

router = APIRouter(prefix="/verify", tags=["verify"])


async def run_case(case_id: str, description: str, fixture_path: str, expected_decision: Decision) -> VerifyResult:
    """Run a single verify case."""
    start = time.time()
    path = Path(fixture_path)

    if not path.exists():
        return VerifyResult(
            case_id=case_id,
            description=description,
            expected_decision=expected_decision,
            passed=False,
            duration_seconds=time.time() - start,
            details={"error": f"Fixture file not found: {fixture_path}"},
        )

    try:
        result = await pipeline.analyze_file(path)
        decisions = result.get("decisions", [])

        # Check if any decision matches expected type
        actual_decisions = set(d.get("decision") for d in decisions)
        expected_value = expected_decision.value

        passed = expected_value in actual_decisions

        return VerifyResult(
            case_id=case_id,
            description=description,
            expected_decision=expected_decision,
            actual_decision=Decision(expected_value) if passed else (
                Decision(next(iter(actual_decisions))) if actual_decisions else None
            ),
            passed=passed,
            duration_seconds=round(time.time() - start, 2),
            details={
                "total_decisions": len(decisions),
                "decision_types": dict((d, list(actual_decisions).count(d)) for d in actual_decisions),
                "summary": result.get("summary", {}),
            },
        )
    except Exception as e:
        return VerifyResult(
            case_id=case_id,
            description=description,
            expected_decision=expected_decision,
            passed=False,
            duration_seconds=round(time.time() - start, 2),
            details={"error": str(e)},
        )


@router.post("")
async def run_verify():
    """Run all 5 verify test cases.

    Returns formatted results with pass/fail for each case.
    """
    fixture_dir = Path("verify/fixtures")
    fixture_dir.mkdir(parents=True, exist_ok=True)

    # Define test cases
    cases = [
        {
            "case_id": "V1",
            "description": "Whitespace normalization → AUTO",
            "fixture": str(fixture_dir / "v1_whitespace.csv"),
            "expected": Decision.AUTO,
        },
        {
            "case_id": "V2",
            "description": "Date format normalization → AUTO",
            "fixture": str(fixture_dir / "v2_date_format.csv"),
            "expected": Decision.AUTO,
        },
        {
            "case_id": "V3",
            "description": "Duplicate key detection → AUTO/BLOCK",
            "fixture": str(fixture_dir / "v3_duplicate.csv"),
            "expected": Decision.AUTO,
        },
        {
            "case_id": "V4",
            "description": "Factual uncertainty → ESCALATE",
            "fixture": str(fixture_dir / "v4_factual_uncertainty.csv"),
            "expected": Decision.ESCALATE,
        },
        {
            "case_id": "V5",
            "description": "Authority escalation → ESCALATE",
            "fixture": str(fixture_dir / "v5_authority.csv"),
            "expected": Decision.ESCALATE,
        },
    ]

    results = []
    for case in cases:
        result = await run_case(
            case["case_id"],
            case["description"],
            case["fixture"],
            case["expected"],
        )
        results.append(result)

    # Summary
    routine_pass = sum(1 for r in results[:3] if r.passed)
    escalation_pass = sum(1 for r in results[3:] if r.passed)
    total_pass = sum(1 for r in results if r.passed)

    return {
        "title": "DataGuard Verify",
        "timestamp": datetime.utcnow().isoformat(),
        "cases": [r.model_dump() for r in results],
        "routine_automation": f"{routine_pass}/3",
        "escalation": f"{escalation_pass}/2",
        "total": f"{total_pass}/5",
        "overall_pass": total_pass >= 4,
    }
