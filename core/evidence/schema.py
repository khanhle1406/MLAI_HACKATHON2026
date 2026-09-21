"""Core evidence data models — the most important abstraction in DataGuard.

Every detector, LLM agent, and human review produces evidence items
conforming to this schema. Evidence flows into the Evidence Registry,
then into D-S fusion, and finally into the Autonomy Gate.

INVARIANT: LLM output is evidence, never authority.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Where the evidence came from."""
    DETERMINISTIC = "deterministic"
    STATISTICAL = "statistical"
    RELATIONAL = "relational"
    SEMANTIC = "semantic"
    HUMAN = "human"


class Claim(str, Enum):
    """What the evidence claims about the cell/row."""
    POSSIBLE_ERROR = "possible_error"
    LIKELY_CLEAN = "likely_clean"
    UNCERTAIN = "uncertain"


class CalibrationStatus(str, Enum):
    VALIDATED = "VALIDATED"
    UNCALIBRATED = "UNCALIBRATED"


class DistributionStatus(str, Enum):
    IN_DISTRIBUTION = "IN_DISTRIBUTION"
    OOD = "OOD"


class EvidenceItem(BaseModel):
    """Standardized evidence from any detector or agent.

    This is the lingua franca of DataGuard. Every module that produces
    evidence must output instances of this model.
    """
    evidence_id: str = Field(default_factory=lambda: f"ev_{uuid4().hex[:12]}")
    dataset_version: str = ""
    row_id: int
    column: str
    detector: str
    source_type: SourceType
    claim: Claim
    score: float = Field(ge=0.0, le=1.0, description="Strength of evidence [0, 1]")
    support: dict[str, Any] = Field(
        default_factory=dict,
        description="Supporting data: observed_value, expected_value, reason_codes, etc.",
    )
    reference_verified: bool = Field(
        default=False,
        description="Whether table references in this evidence have been verified by critic.",
    )
    calibration_status: CalibrationStatus = CalibrationStatus.UNCALIBRATED
    distribution_status: DistributionStatus = DistributionStatus.IN_DISTRIBUTION
    counterevidence: list[str] = Field(
        default_factory=list,
        description="Reasons why this might NOT be an issue. MUST be populated.",
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class UncertaintyType(str, Enum):
    """Three categories of uncertainty — maps to Board A requirements."""
    FACTUAL = "factual"       # Cannot establish if value is correct
    POLICY = "policy"         # No authoritative rule resolves the case
    AUTHORITY = "authority"   # AI knows action but lacks authority


class ActionImpact(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Decision(str, Enum):
    AUTO = "AUTO"
    ESCALATE = "ESCALATE"
    BLOCK = "BLOCK"


class ConstraintSource(str, Enum):
    """Three layers of truth — MANDATORY separation."""
    OBSERVED = "OBSERVED"          # Facts derived from data
    INFERRED = "INFERRED"          # AI-generated hypotheses (UNVERIFIED)
    AUTHORITATIVE = "AUTHORITATIVE"  # Human-approved policy (can authorize AUTO)


class ConstraintStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class PolicyStatus(str, Enum):
    PROPOSED = "PROPOSED"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MISSING = "MISSING"


class ReviewAction(str, Enum):
    APPROVE = "APPROVE"
    EDIT = "EDIT"
    REJECT = "REJECT"


class DecisionContext(BaseModel):
    """Input to the Autonomy Gate — deterministic decision code.

    This model collects all signals needed for the gate to produce
    AUTO / ESCALATE / BLOCK. No ML happens here.
    """
    unsupported_input: bool = False
    security_violation: bool = False
    authority_level: int = 0
    required_authority: int = 0
    action_impact: ActionImpact = ActionImpact.LOW
    policy_status: PolicyStatus = PolicyStatus.MISSING
    out_of_distribution: bool = False
    conformal_abstain: bool = False
    ds_conflict: float = 0.0
    max_conflict: float = 0.3
    ds_ignorance: float = 0.0
    max_ignorance: float = 0.4
    ds_belief_error: float = 0.0
    ds_belief_clean: float = 0.0
    reference_verified: bool = False
    repair_is_reversible: bool = False
    repair_is_deterministic: bool = False
    validated_autonomy_condition: bool = False
    uncertainty_type: UncertaintyType | None = None


class AuditEventType(str, Enum):
    UPLOAD = "UPLOAD"
    PROFILE = "PROFILE"
    DETECT = "DETECT"
    DECIDE = "DECIDE"
    AUTO_FIX = "AUTO_FIX"
    ESCALATE = "ESCALATE"
    BLOCK = "BLOCK"
    REVIEW = "REVIEW"
    COMMIT = "COMMIT"
    ROLLBACK = "ROLLBACK"
    POLICY_CHANGE = "POLICY_CHANGE"


class ColumnProfile(BaseModel):
    """Profile of a single column."""
    column_name: str
    column_index: int
    observed_type: str
    semantic_type: str | None = None
    semantic_confidence: float = 0.0
    missing_rate: float = 0.0
    unique_rate: float = 0.0
    cardinality: int = 0
    statistics: dict[str, Any] = Field(default_factory=dict)
    pattern_distribution: dict[str, float] = Field(default_factory=dict)
    examples: list[Any] = Field(default_factory=list)
    pii_likelihood: float = 0.0
    date_likelihood: float = 0.0


class DatasetProfile(BaseModel):
    """Complete profile of an uploaded dataset."""
    dataset_id: str
    name: str
    file_format: str
    encoding: str = "utf-8"
    row_count: int
    column_count: int
    sha256: str
    columns: list[ColumnProfile]
    table_hypothesis: str | None = None
    table_confidence: float = 0.0
    parser_warnings: list[str] = Field(default_factory=list)


class VerifyResult(BaseModel):
    """Result of a single verify test case."""
    case_id: str
    description: str
    expected_decision: Decision
    actual_decision: Decision | None = None
    passed: bool = False
    duration_seconds: float = 0.0
    details: dict[str, Any] = Field(default_factory=dict)
