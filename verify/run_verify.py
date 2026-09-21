#!/usr/bin/env python3
"""DataGuard Verify Harness — One-click competition verification.

Usage:
    python verify/run_verify.py [--api-url http://localhost:8000]

Prints a formatted results table with PASS/FAIL for each case.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime

import httpx


def run(api_url: str = "http://localhost:8000"):
    """Run verify suite against the API."""
    print("╔══════════════════════════════════════════════════════╗")
    print("║       DataGuard Verify Harness — Competition        ║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):>39s} ║")
    print(f"║  API:       {api_url:>39s} ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    fixtures = [
        ("V1", "Whitespace normalization", "verify/fixtures/v1_whitespace.csv", "AUTO"),
        ("V2", "Date format normalization", "verify/fixtures/v2_date_format.csv", "AUTO"),
        ("V3", "Duplicate key detection", "verify/fixtures/v3_duplicate.csv", "AUTO/ESC"),
        ("V4", "Factual uncertainty (outlier)", "verify/fixtures/v4_factual_uncertainty.csv", "ESC"),
        ("V5", "Authority escalation (financial)", "verify/fixtures/v5_authority.csv", "ESC"),
    ]

    results = []
    total_pass = 0

    for case_id, description, fixture_path, expected in fixtures:
        try:
            with open(fixture_path, "rb") as f:
                resp = httpx.post(
                    f"{api_url}/api/datasets",
                    files={"file": (fixture_path.split("/")[-1], f, "text/csv")},
                    timeout=30,
                )
            data = resp.json()
            summary = data.get("summary", {})

            auto = summary.get("auto_count", 0)
            esc = summary.get("escalate_count", 0)
            blk = summary.get("block_count", 0)
            elapsed = summary.get("elapsed_seconds", 0)

            # Determine pass
            if expected == "AUTO":
                passed = auto > 0
            elif expected == "ESC":
                passed = esc > 0
            elif expected == "AUTO/ESC":
                passed = auto > 0 or esc > 0
            else:
                passed = False

            if passed:
                total_pass += 1

            mark = "✅ PASS" if passed else "❌ FAIL"
            results.append((case_id, description, mark, f"A={auto} E={esc} B={blk}", f"{elapsed}s"))

        except Exception as e:
            results.append((case_id, description, "❌ ERROR", str(e)[:30], "—"))

    # Print table
    print(f"{'Case':<5} {'Description':<35} {'Result':<10} {'Decisions':<15} {'Time':<8}")
    print("─" * 75)
    for r in results:
        print(f"{r[0]:<5} {r[1]:<35} {r[2]:<10} {r[3]:<15} {r[4]:<8}")
    print("─" * 75)

    # Summary
    print(f"\n  Score: {total_pass}/{len(fixtures)}")
    status = "PASS ✅" if total_pass >= 4 else "FAIL ❌"
    print(f"  Overall: {status}")
    print()

    return total_pass


if __name__ == "__main__":
    api = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].startswith("http") else "http://localhost:8000"
    score = run(api)
    sys.exit(0 if score >= 4 else 1)
