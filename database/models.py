"""SQLAlchemy ORM models for DataGuard.

All core entities: datasets, versions, evidence, decisions, reviews,
audit events, policies, constraints, jobs, feedback, calibration.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def gen_uuid():
    return uuid.uuid4()


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    original_filename = Column(String(500))
    file_format = Column(String(20))
    encoding = Column(String(50))
    row_count = Column(Integer)
    column_count = Column(Integer)
    sha256 = Column(String(64))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    created_by = Column(String(100), default="system")
    status = Column(String(20), default="ACTIVE")

    versions = relationship("DatasetVersion", back_populates="dataset")
    column_profiles = relationship("ColumnProfileDB", back_populates="dataset")
    jobs = relationship("Job", back_populates="dataset")


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    parent_version_id = Column(UUID(as_uuid=True), ForeignKey("dataset_versions.id"), nullable=True)
    storage_path = Column(Text, nullable=False)
    sha256 = Column(String(64))
    actor = Column(String(100))
    reason = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("dataset_id", "version_number"),)

    dataset = relationship("Dataset", back_populates="versions")


class ColumnProfileDB(Base):
    __tablename__ = "column_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False)
    column_name = Column(String(255))
    column_index = Column(Integer)
    observed_type = Column(String(50))
    semantic_type = Column(String(100))
    semantic_confidence = Column(Float)
    missing_rate = Column(Float)
    unique_rate = Column(Float)
    cardinality = Column(Integer)
    statistics = Column(JSON)
    pattern_distribution = Column(JSON)
    examples = Column(JSON)
    pii_likelihood = Column(Float)
    date_likelihood = Column(Float)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    dataset = relationship("Dataset", back_populates="column_profiles")


class Constraint(Base):
    __tablename__ = "constraints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"))
    column_name = Column(String(255))
    constraint_type = Column(String(50))
    rule = Column(JSON, nullable=False)
    source = Column(String(20), nullable=False)  # OBSERVED, INFERRED, AUTHORITATIVE
    status = Column(String(20), default="UNVERIFIED")
    version = Column(Integer, default=1)
    owner = Column(String(100))
    approved_by = Column(String(100))
    approved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Policy(Base):
    __tablename__ = "policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    policy_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(255))
    description = Column(Text)
    scope = Column(JSON)
    rules = Column(JSON, nullable=False)
    allowed_actions = Column(JSON)
    authority_level = Column(String(20))
    status = Column(String(20), default="PROPOSED")
    version = Column(Integer, default=1)
    owner = Column(String(100))
    approved_by = Column(String(100))
    effective_from = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    dataset_version_id = Column(UUID(as_uuid=True), ForeignKey("dataset_versions.id"))
    row_id = Column(Integer)
    column_name = Column(String(255))
    detector = Column(String(100), nullable=False)
    source_type = Column(String(30), nullable=False)
    claim = Column(String(30), nullable=False)
    score = Column(Float)
    support = Column(JSON)
    reference_verified = Column(Boolean, default=False)
    calibration_status = Column(String(20))
    distribution_status = Column(String(20))
    counterevidence = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class DecisionRecord(Base):
    __tablename__ = "decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"))
    dataset_version = Column(Integer)
    row_id = Column(Integer)
    column_name = Column(String(255))
    old_value = Column(Text)
    new_value = Column(Text)
    decision = Column(String(20), nullable=False)  # AUTO, ESCALATE, BLOCK
    risk_level = Column(String(20))
    belief_error = Column(Float)
    belief_clean = Column(Float)
    ignorance = Column(Float)
    conflict_k = Column(Float)
    uncertainty_type = Column(String(30))
    reason_codes = Column(JSON)
    question = Column(Text)  # Concrete question for human
    policy_id = Column(String(100))
    action_type = Column(String(50))
    reversible = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    reviews = relationship("Review", back_populates="decision")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    decision_id = Column(UUID(as_uuid=True), ForeignKey("decisions.id"), nullable=False)
    reviewer = Column(String(100), nullable=False)
    action = Column(String(20), nullable=False)  # APPROVE, EDIT, REJECT
    edited_value = Column(Text)
    comment = Column(Text)
    confidence = Column(Float)
    review_time_seconds = Column(Float)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    decision = relationship("DecisionRecord", back_populates="reviews")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    event_type = Column(String(50), nullable=False)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True)
    decision_id = Column(UUID(as_uuid=True), ForeignKey("decisions.id"), nullable=True)
    actor = Column(String(100))
    details = Column(JSON)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"))
    status = Column(String(30), default="PENDING")
    mode = Column(String(20), default="analyze")
    autonomy_enabled = Column(Boolean, default=True)
    budget_usd = Column(Float, default=1.0)
    progress = Column(JSON)
    result_summary = Column(JSON)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    dataset = relationship("Dataset", back_populates="jobs")


class FeedbackEvent(Base):
    __tablename__ = "feedback_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    decision_id = Column(UUID(as_uuid=True), ForeignKey("decisions.id"))
    feedback_type = Column(String(30))
    original_decision = Column(String(20))
    corrected_decision = Column(String(20))
    comment = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class CalibrationVersion(Base):
    __tablename__ = "calibration_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    version = Column(Integer)
    thresholds = Column(JSON)
    dataset_family = Column(String(100))
    approved_by = Column(String(100))
    validation_metrics = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
