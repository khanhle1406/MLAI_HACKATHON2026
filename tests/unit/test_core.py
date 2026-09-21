"""Unit tests for DataGuard core components."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import polars as pl
import pytest


class TestEvidenceSchema:
    """Test evidence schema and enums."""

    def test_evidence_item_creation(self):
        from core.evidence.schema import Claim, EvidenceItem, SourceType

        ev = EvidenceItem(
            row_id=0,
            column="name",
            detector="test_detector",
            source_type=SourceType.DETERMINISTIC,
            claim=Claim.POSSIBLE_ERROR,
            score=0.95,
            support={"reason_codes": ["test"]},
            reference_verified=True,
            counterevidence=["might be correct"],
        )
        assert ev.score == 0.95
        assert ev.claim == Claim.POSSIBLE_ERROR
        assert len(ev.counterevidence) == 1

    def test_decision_enum(self):
        from core.evidence.schema import Decision

        assert Decision.AUTO.value == "AUTO"
        assert Decision.ESCALATE.value == "ESCALATE"
        assert Decision.BLOCK.value == "BLOCK"


class TestDempsterShafer:
    """Test D-S fusion module."""

    def test_single_evidence(self):
        from core.fusion.dempster_shafer import fuse_single_cell

        result = fuse_single_cell([(0.9, "detector_a")])
        assert result["belief_error"] == pytest.approx(0.9, abs=0.01)
        assert result["conflict"] == 0.0

    def test_agreeing_evidence(self):
        from core.fusion.dempster_shafer import fuse_single_cell

        result = fuse_single_cell([(0.8, "det_a"), (0.7, "det_b")])
        assert result["belief_error"] > 0.8  # Combined should be stronger

    def test_conflicting_evidence(self):
        from core.fusion.dempster_shafer import fuse_single_cell

        result = fuse_single_cell([(0.9, "det_a"), (-0.8, "det_b")])
        assert result["conflict"] > 0.1  # Should detect conflict

    def test_same_family_cautious(self):
        from core.fusion.dempster_shafer import fuse_single_cell

        result = fuse_single_cell([(0.8, "det_a"), (0.6, "det_a")])
        # Same family uses cautious (min) instead of Dempster
        assert result["belief_error"] <= 0.8


class TestAutonomyGate:
    """Test the deterministic Autonomy Gate."""

    def test_auto_decision(self):
        from core.decisions.autonomy_gate import autonomy_gate
        from core.evidence.schema import (
            ActionImpact,
            DecisionContext,
            Decision,
            PolicyStatus,
        )

        ctx = DecisionContext(
            ds_conflict=0.0,
            ds_ignorance=0.1,
            ds_belief_error=0.9,
            ds_belief_clean=0.05,
            action_impact=ActionImpact.LOW,
            policy_status=PolicyStatus.ACTIVE,
            reference_verified=True,
            repair_is_reversible=True,
            repair_is_deterministic=True,
            validated_autonomy_condition=True,
        )
        decision = autonomy_gate(ctx)
        assert decision == Decision.AUTO

    def test_escalate_high_impact(self):
        from core.decisions.autonomy_gate import autonomy_gate
        from core.evidence.schema import (
            ActionImpact,
            DecisionContext,
            Decision,
            PolicyStatus,
        )

        ctx = DecisionContext(
            ds_conflict=0.0,
            ds_ignorance=0.1,
            ds_belief_error=0.9,
            ds_belief_clean=0.05,
            action_impact=ActionImpact.HIGH,
            policy_status=PolicyStatus.ACTIVE,
            reference_verified=True,
            repair_is_reversible=False,
            repair_is_deterministic=True,
            validated_autonomy_condition=False,
        )
        decision = autonomy_gate(ctx)
        assert decision == Decision.ESCALATE

    def test_block_unsupported(self):
        from core.decisions.autonomy_gate import autonomy_gate
        from core.evidence.schema import (
            ActionImpact,
            DecisionContext,
            Decision,
            PolicyStatus,
        )

        ctx = DecisionContext(
            ds_conflict=0.0,
            ds_ignorance=0.0,
            ds_belief_error=0.0,
            ds_belief_clean=0.0,
            action_impact=ActionImpact.LOW,
            policy_status=PolicyStatus.ACTIVE,
            unsupported_input=True,
        )
        decision = autonomy_gate(ctx)
        assert decision == Decision.BLOCK

    def test_gate_is_deterministic(self):
        """Invariant: same input → same output. Always."""
        from core.decisions.autonomy_gate import autonomy_gate
        from core.evidence.schema import (
            ActionImpact,
            DecisionContext,
            PolicyStatus,
        )

        ctx = DecisionContext(
            ds_conflict=0.15,
            ds_ignorance=0.3,
            ds_belief_error=0.7,
            ds_belief_clean=0.1,
            action_impact=ActionImpact.MEDIUM,
            policy_status=PolicyStatus.ACTIVE,
        )
        # Run 100 times — must always produce same result
        decisions = [autonomy_gate(DecisionContext(**ctx.__dict__)) for _ in range(100)]
        assert len(set(d.value for d in decisions)) == 1


class TestDetectors:
    """Test individual detectors."""

    def test_whitespace_detector(self):
        from core.detectors.pattern.format_consistency import WhitespaceDetector

        df = pl.DataFrame({"name": [" hello ", "world", "  test  "]})
        det = WhitespaceDetector()
        evidence = det.detect(df)
        assert len(evidence) == 2  # " hello " and "  test  "

    def test_null_detector(self):
        from core.detectors.missingness.null_detector import NullDetector

        df = pl.DataFrame({"val": [1, None, 3, None, 5]})
        det = NullDetector()
        evidence = det.detect(df)
        assert len(evidence) == 2

    def test_outlier_detector(self):
        from core.detectors.statistical.outlier import OutlierDetector

        df = pl.DataFrame({"salary": [10, 12, 11, 13, 100]})
        det = OutlierDetector()
        evidence = det.detect(df)
        assert len(evidence) >= 1  # 100 should be flagged

    def test_duplicate_key_detector(self):
        from core.detectors.relational.duplicate_key import DuplicateKeyDetector

        df = pl.DataFrame({"employee_id": ["E001", "E002", "E001", "E003"]})
        det = DuplicateKeyDetector()
        evidence = det.detect(df)
        assert len(evidence) >= 1


class TestIngestion:
    """Test file ingestion."""

    def test_parse_csv(self):
        from core.ingestion.parser import parse_file

        path = Path("verify/fixtures/v1_whitespace.csv")
        df, meta = parse_file(path)
        assert len(df) == 5
        assert len(df.columns) == 4
        assert meta["file_format"] == "csv"


class TestPipeline:
    """Test end-to-end pipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        from core.orchestrator.pipeline import pipeline

        path = Path("verify/fixtures/v1_whitespace.csv")
        result = await pipeline.analyze_file(path)
        assert result["status"] == "COMPLETED"
        assert result["summary"]["auto_count"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
