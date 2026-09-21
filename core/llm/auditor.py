"""LLM-powered Auditor Agent.

Generates human-readable escalation questions for uncertain decisions.
Provides second-opinion evidence (but NEVER authority).

INVARIANT: LLM output is encoded as EvidenceItem with source_type=LLM.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from core.evidence.schema import Claim, EvidenceItem, SourceType
from core.llm.client import get_llm_client

logger = logging.getLogger(__name__)

AUDITOR_SYSTEM_PROMPT = """You are DataGuard Auditor, a data quality assessment AI.

Your role is to provide a SECOND OPINION on data quality issues.
You are NOT the decision maker. Your output is EVIDENCE that will be
weighed alongside other evidence sources using Dempster-Shafer theory.

Rules:
1. Be honest about uncertainty. Say "I'm not sure" when appropriate.
2. Consider both "this is an error" and "this is correct" hypotheses.
3. Provide concrete reasoning.
4. Output valid JSON only.

Output format:
{
  "assessment": "error" | "likely_error" | "uncertain" | "likely_clean" | "clean",
  "confidence": 0.0 to 1.0,
  "reasoning": "string explaining your assessment",
  "counterarguments": ["list of reasons this might be wrong"],
  "suggested_action": "string describing what to do"
}"""


async def get_auditor_evidence(
    column: str,
    value: str,
    column_profile: dict[str, Any] | None = None,
    context_rows: list[str] | None = None,
) -> EvidenceItem | None:
    """Get LLM auditor evidence for a suspicious value.

    Returns an EvidenceItem with source_type=LLM, or None if call fails.
    """
    client = get_llm_client()

    profile_str = ""
    if column_profile:
        profile_str = f"""
Column profile:
- Type: {column_profile.get('observed_type', 'unknown')}
- Semantic: {column_profile.get('semantic_type', 'unknown')}  
- Missing rate: {column_profile.get('missing_rate', 0):.2%}
- Unique rate: {column_profile.get('unique_rate', 0):.2%}
- Examples: {column_profile.get('examples', [])}"""

    context_str = ""
    if context_rows:
        context_str = f"\nNearby values in this column: {', '.join(context_rows[:10])}"

    user_prompt = f"""Assess this data value for quality issues:

Column: {column}
Value: "{value}"
{profile_str}
{context_str}

Is this value an error, or is it legitimate? Provide your assessment as JSON."""

    try:
        result = client.chat(
            messages=[
                {"role": "system", "content": AUDITOR_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
        )

        content = result.get("content", "{}")
        parsed = json.loads(content)

        assessment = parsed.get("assessment", "uncertain")
        confidence = float(parsed.get("confidence", 0.5))

        # Map assessment to claim
        claim_map = {
            "error": (Claim.POSSIBLE_ERROR, confidence),
            "likely_error": (Claim.POSSIBLE_ERROR, confidence * 0.8),
            "uncertain": (Claim.UNCERTAIN, 0.5),
            "likely_clean": (Claim.CONSISTENT, confidence * 0.8),
            "clean": (Claim.CONSISTENT, confidence),
        }
        claim, score = claim_map.get(assessment, (Claim.UNCERTAIN, 0.5))

        return EvidenceItem(
            row_id=-1,  # Will be set by caller
            column=column,
            detector="llm_auditor",
            source_type=SourceType.LLM,
            claim=claim,
            score=round(score, 4),
            support={
                "assessment": assessment,
                "confidence": confidence,
                "reasoning": parsed.get("reasoning", ""),
                "suggested_action": parsed.get("suggested_action", ""),
                "model": result.get("model", "unknown"),
                "cost_usd": result.get("cost_usd", 0.0),
                "mock": result.get("mock", False),
            },
            reference_verified=False,  # LLM output is NOT verified reference
            counterevidence=parsed.get("counterarguments", []),
        )

    except Exception as e:
        logger.error(f"Auditor agent failed: {e}")
        return None
