"""Autonomy Gate — The final authority in DataGuard.

This module implements the deterministic decision logic that determines
whether the system should AUTO-fix, ESCALATE to human, or BLOCK.

CRITICAL INVARIANT: This code MUST remain pure deterministic Python.
No ML, no LLM calls, no probabilistic inference. Only boolean checks
on validated evidence signals.

The gate answers: "Given the evidence, policy, authority, and risk,
is the AI permitted to act autonomously?"
"""

from __future__ import annotations

import logging
from datetime import datetime

from core.evidence.schema import (
    ActionImpact,
    Decision,
    DecisionContext,
    PolicyStatus,
    UncertaintyType,
)

logger = logging.getLogger(__name__)


def autonomy_gate(ctx: DecisionContext) -> Decision:
    """Deterministic, inspectable decision gate.

    Returns AUTO, ESCALATE, or BLOCK based on the accumulated evidence
    and policy signals in the DecisionContext.

    The default behavior is ESCALATE (conservative). AUTO requires ALL
    safety conditions to be satisfied.

    Args:
        ctx: DecisionContext with all evidence signals.

    Returns:
        Decision.AUTO, Decision.ESCALATE, or Decision.BLOCK
    """
    # ── BLOCK conditions (immediate, no further evaluation) ──
    if ctx.unsupported_input:
        logger.info("GATE → BLOCK: unsupported input")
        return Decision.BLOCK

    if ctx.security_violation:
        logger.info("GATE → BLOCK: security violation detected")
        return Decision.BLOCK

    # ── ESCALATE conditions (ordered by severity) ──

    # Authority check
    if ctx.authority_level < ctx.required_authority:
        logger.info(
            "GATE → ESCALATE: insufficient authority "
            f"(have={ctx.authority_level}, need={ctx.required_authority})"
        )
        ctx.uncertainty_type = UncertaintyType.AUTHORITY
        return Decision.ESCALATE

    # High-impact action always requires human
    if ctx.action_impact == ActionImpact.HIGH:
        logger.info("GATE → ESCALATE: high-impact action requires human approval")
        ctx.uncertainty_type = UncertaintyType.AUTHORITY
        return Decision.ESCALATE

    # ── FAST-PATH: Safe deterministic repairs ──
    # Deterministic + reversible + low-impact repairs can bypass policy
    # and ignorance checks. Ignorance measures "not enough evidence to
    # decide" — but for known-safe transforms (whitespace, date format),
    # we don't need more evidence. We know what to do.
    if (
        ctx.repair_is_deterministic
        and ctx.repair_is_reversible
        and ctx.action_impact == ActionImpact.LOW
        and not ctx.out_of_distribution
        and ctx.ds_conflict < ctx.max_conflict
    ):
        logger.info("GATE → AUTO: safe deterministic repair (low-impact, reversible)")
        return Decision.AUTO

    # Policy must be active and approved
    if ctx.policy_status != PolicyStatus.ACTIVE:
        logger.info(f"GATE → ESCALATE: policy status is {ctx.policy_status}")
        ctx.uncertainty_type = UncertaintyType.POLICY
        return Decision.ESCALATE

    # Out-of-distribution data
    if ctx.out_of_distribution:
        logger.info("GATE → ESCALATE: data is out-of-distribution")
        ctx.uncertainty_type = UncertaintyType.FACTUAL
        return Decision.ESCALATE

    # Conformal prediction says abstain
    if ctx.conformal_abstain:
        logger.info("GATE → ESCALATE: conformal prediction recommends abstention")
        ctx.uncertainty_type = UncertaintyType.FACTUAL
        return Decision.ESCALATE

    # D-S conflict too high (evidence sources disagree)
    if ctx.ds_conflict >= ctx.max_conflict:
        logger.info(
            f"GATE → ESCALATE: D-S conflict too high "
            f"(K={ctx.ds_conflict:.3f} >= threshold={ctx.max_conflict:.3f})"
        )
        ctx.uncertainty_type = UncertaintyType.FACTUAL
        return Decision.ESCALATE

    # D-S ignorance too high (not enough evidence)
    if ctx.ds_ignorance >= ctx.max_ignorance:
        logger.info(
            f"GATE → ESCALATE: D-S ignorance too high "
            f"(m_Ω={ctx.ds_ignorance:.3f} >= threshold={ctx.max_ignorance:.3f})"
        )
        ctx.uncertainty_type = UncertaintyType.FACTUAL
        return Decision.ESCALATE

    # LLM references not verified by critic
    if not ctx.reference_verified:
        logger.info("GATE → ESCALATE: evidence references not verified")
        ctx.uncertainty_type = UncertaintyType.FACTUAL
        return Decision.ESCALATE

    # ── AUTO conditions (must satisfy ALL) ──

    # Safe auto-fix: deterministic + reversible
    if ctx.repair_is_reversible and ctx.repair_is_deterministic:
        logger.info("GATE → AUTO: repair is deterministic and reversible")
        return Decision.AUTO

    # Validated autonomy condition (e.g., calibrated threshold passed)
    if ctx.validated_autonomy_condition:
        logger.info("GATE → AUTO: validated autonomy condition met")
        return Decision.AUTO

    # ── Conservative default ──
    logger.info("GATE → ESCALATE: no AUTO condition satisfied (conservative default)")
    ctx.uncertainty_type = UncertaintyType.FACTUAL
    return Decision.ESCALATE


def format_escalation_question(
    row_id: int,
    column: str,
    observed_value: str,
    issue_description: str,
    evidence_summary: list[str],
    uncertainty_type: UncertaintyType,
    proposed_action: str | None = None,
) -> str:
    """Generate a concrete, actionable question for the human reviewer.

    Board A requirement: escalation must include a specific question,
    not just "please review this row."
    """
    evidence_text = "\n".join(f"  - {e}" for e in evidence_summary)

    if uncertainty_type == UncertaintyType.FACTUAL:
        question = (
            f"Row {row_id}, column '{column}': value = '{observed_value}'\n"
            f"Issue: {issue_description}\n"
            f"Evidence:\n{evidence_text}\n\n"
            f"Question: Is this value correct, or should it be changed? "
            f"The system cannot determine the correct value from available evidence."
        )
    elif uncertainty_type == UncertaintyType.POLICY:
        question = (
            f"Row {row_id}, column '{column}': value = '{observed_value}'\n"
            f"Issue: {issue_description}\n"
            f"Evidence:\n{evidence_text}\n\n"
            f"Question: There is no approved policy covering this case. "
            f"Should a policy be created? What should the rule be?"
        )
    elif uncertainty_type == UncertaintyType.AUTHORITY:
        action_text = f" ({proposed_action})" if proposed_action else ""
        question = (
            f"Row {row_id}, column '{column}': value = '{observed_value}'\n"
            f"Issue: {issue_description}\n"
            f"Evidence:\n{evidence_text}\n\n"
            f"Question: The system has identified the appropriate action{action_text} "
            f"but does not have authority to execute it. Do you authorize this action?"
        )
    else:
        question = (
            f"Row {row_id}, column '{column}': value = '{observed_value}'\n"
            f"Issue: {issue_description}\n"
            f"Evidence:\n{evidence_text}\n\n"
            f"Question: Please review this case and decide the appropriate action."
        )

    return question
