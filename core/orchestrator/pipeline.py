"""Main analysis pipeline — orchestrates the Progressive Evidence Cascade.

This is the main entry point that ties all modules together:
  Ingestion → Profiling → Detection → Fusion → Autonomy Gate → Action

INVARIANT: This pipeline enforces all safety invariants.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import polars as pl

from core.audit.ledger import audit_ledger
from core.decisions.autonomy_gate import autonomy_gate, format_escalation_question
from core.evidence.schema import (
    ActionImpact,
    Claim,
    DatasetProfile,
    Decision,
    DecisionContext,
    EvidenceItem,
    PolicyStatus,
    SourceType,
    UncertaintyType,
)
from core.fusion.dempster_shafer import fuse_single_cell
from core.ingestion.parser import parse_file
from core.profiling.column_profiler import profile_dataframe
from core.assistant.report_generator import generate_assistant_report

logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """Orchestrates the full DataGuard analysis pipeline."""

    def __init__(self):
        self._detectors = []
        self._load_detectors()

    def _load_detectors(self):
        """Load all available detectors."""
        try:
            from core.detectors.missingness.null_detector import (
                DisguisedNullDetector,
                NullDetector,
            )
            from core.detectors.pattern.format_consistency import (
                DateFormatDetector,
                PatternRarityDetector,
                WhitespaceDetector,
            )
            from core.detectors.relational.duplicate_key import (
                DuplicateKeyDetector,
                FDViolationDetector,
            )
            from core.detectors.statistical.outlier import OutlierDetector
            from core.detectors.policy.authority_detector import HighValueDataDetector
            from core.detectors.semantic.type_mismatch import TypeMismatchDetector
            from core.detectors.semantic.near_duplicate import NearDuplicateDetector

            self._detectors = [
                NullDetector(),
                DisguisedNullDetector(),
                WhitespaceDetector(),
                DateFormatDetector(),
                PatternRarityDetector(),
                OutlierDetector(),
                TypeMismatchDetector(),
                NearDuplicateDetector(),
                DuplicateKeyDetector(),
                FDViolationDetector(),
                HighValueDataDetector(),
            ]
            logger.info(f"Loaded {len(self._detectors)} detectors")
        except Exception as e:
            logger.error(f"Failed to load detectors: {e}")
            self._detectors = []

    async def analyze_file(
        self,
        file_path: Path,
        dataset_id: str | None = None,
        autonomy_enabled: bool = True,
    ) -> dict[str, Any]:
        """Run full analysis pipeline on a file.

        Steps:
          0. Security + Ingestion
          1. Table Understanding (profiling)
          2-3. Detection (deterministic)
          4. Evidence Collection
          5. D-S Fusion
          6. Autonomy Gate decisions
          7. Action (AUTO/ESCALATE/BLOCK)
          8. Audit recording

        Returns:
            Analysis result dict.
        """
        start_time = time.time()
        dataset_id = dataset_id or str(uuid4())

        result = {
            "dataset_id": dataset_id,
            "status": "IN_PROGRESS",
            "profile": None,
            "evidence": [],
            "decisions": [],
            "summary": {},
            "errors": [],
        }

        # ── Step 0: Ingestion ──
        try:
            df, metadata = parse_file(file_path)
            audit_ledger.record("UPLOAD", "system", dataset_id, details=metadata)
        except Exception as e:
            result["status"] = "FAILED"
            result["errors"].append(f"Ingestion failed: {str(e)}")
            return result

        # ── Step 1: Profiling ──
        try:
            column_profiles = profile_dataframe(df)
            profile = DatasetProfile(
                dataset_id=dataset_id,
                name=metadata.get("original_filename", "unknown"),
                file_format=metadata.get("file_format", "unknown"),
                encoding=metadata.get("encoding", "utf-8"),
                row_count=metadata.get("row_count", 0),
                column_count=metadata.get("column_count", 0),
                sha256=metadata.get("sha256", ""),
                columns=column_profiles,
                parser_warnings=metadata.get("parser_warnings", []),
            )
            result["profile"] = profile.model_dump()
            audit_ledger.record("PROFILE", "system", dataset_id, details={
                "row_count": profile.row_count,
                "column_count": profile.column_count,
            })
        except Exception as e:
            result["errors"].append(f"Profiling failed: {str(e)}")
            logger.error(f"Profiling failed: {e}")

        # ── Steps 2-3: Detection ──
        all_evidence: list[EvidenceItem] = []
        for detector in self._detectors:
            try:
                evidence = detector.detect(df)
                all_evidence.extend(evidence)
                logger.info(f"Detector '{detector.name}': found {len(evidence)} evidence items")
            except Exception as e:
                logger.warning(f"Detector '{detector.name}' failed: {e}")

        result["evidence"] = [e.model_dump() for e in all_evidence]
        audit_ledger.record("DETECT", "system", dataset_id, details={
            "total_evidence": len(all_evidence),
            "detectors_run": len(self._detectors),
        })

        # ── Steps 4-6: Group evidence by cell and make decisions ──
        cell_evidence: dict[tuple[int, str], list[EvidenceItem]] = {}
        for ev in all_evidence:
            key = (ev.row_id, ev.column)
            cell_evidence.setdefault(key, []).append(ev)

        decisions = []
        auto_count = 0
        escalate_count = 0
        block_count = 0

        for (row_id, column), evidence_list in cell_evidence.items():
            # D-S fusion for this cell
            fusion_inputs = []
            for ev in evidence_list:
                sign = 1.0 if ev.claim == Claim.POSSIBLE_ERROR else -1.0
                fusion_inputs.append((sign * ev.score, ev.detector.split("_")[0]))

            fusion_result = fuse_single_cell(fusion_inputs)

            # Extract support and repair signals from evidence list
            repair_ev = next(
                (e for e in evidence_list if e.support.get("expected_value") is not None),
                evidence_list[0] if evidence_list else None,
            )
            obs_ev = next(
                (e for e in evidence_list if e.support.get("observed_value") is not None),
                evidence_list[0] if evidence_list else None,
            )
            support = repair_ev.support if repair_ev else {}
            observed_val = obs_ev.support.get("observed_value", "") if obs_ev else ""

            # Check ALL evidence items for repair signals
            is_deterministic_repair = any(
                e.support.get("repair_deterministic", False) for e in evidence_list
            )
            is_reversible_repair = any(
                e.support.get("repair_reversible", False) for e in evidence_list
            )
            action_type = next(
                (e.support.get("action") for e in evidence_list if e.support.get("action")),
                "unknown",
            )

            # Determine action impact
            action_impact = ActionImpact.LOW
            if action_type in ("delete_row", "delete_column", "modify_schema", "verify_authority"):
                action_impact = ActionImpact.HIGH
            elif action_type in ("change_value", "merge_records"):
                action_impact = ActionImpact.MEDIUM

            # Check if any evidence requires elevated authority
            required_authority = max(
                (e.support.get("required_authority", 0) for e in evidence_list),
                default=0,
            )

            ctx = DecisionContext(
                ds_conflict=fusion_result["conflict"],
                ds_ignorance=fusion_result["ignorance"],
                ds_belief_error=fusion_result["belief_error"],
                ds_belief_clean=fusion_result["belief_clean"],
                action_impact=action_impact,
                policy_status=PolicyStatus.ACTIVE if is_deterministic_repair else PolicyStatus.MISSING,
                reference_verified=all(e.reference_verified for e in evidence_list),
                repair_is_reversible=is_reversible_repair,
                repair_is_deterministic=is_deterministic_repair,
                validated_autonomy_condition=is_deterministic_repair and is_reversible_repair,
                required_authority=required_authority,
            )

            decision = autonomy_gate(ctx)

            # Format the decision record
            decision_record = {
                "decision_id": str(uuid4()),
                "dataset_id": dataset_id,
                "row_id": row_id,
                "column": column,
                "old_value": str(observed_val),
                "new_value": str(support.get("expected_value", "")) if decision == Decision.AUTO else None,
                "decision": decision.value,
                "risk_level": action_impact.value,
                "belief_error": round(fusion_result["belief_error"], 4),
                "belief_clean": round(fusion_result["belief_clean"], 4),
                "ignorance": round(fusion_result["ignorance"], 4),
                "conflict_k": round(fusion_result["conflict"], 4),
                "uncertainty_type": ctx.uncertainty_type.value if ctx.uncertainty_type else None,
                "reason_codes": [e.support.get("reason_codes", []) for e in evidence_list],
                "action_type": action_type,
                "reversible": is_reversible_repair,
                "evidence_count": len(evidence_list),
            }

            # Generate escalation question if needed
            if decision == Decision.ESCALATE:
                question = format_escalation_question(
                    row_id=row_id,
                    column=column,
                    observed_value=str(support.get("observed_value", "")),
                    issue_description=", ".join(
                        str(code) for e in evidence_list
                        for code in (e.support.get("reason_codes", []) if isinstance(e.support.get("reason_codes"), list) else [])
                        if code is not None
                    ),
                    evidence_summary=[
                        f"{e.detector}: {e.claim.value} (score={e.score:.2f})"
                        for e in evidence_list
                    ],
                    uncertainty_type=ctx.uncertainty_type or UncertaintyType.FACTUAL,
                )
                decision_record["question"] = question

            decisions.append(decision_record)

            # Count decisions
            if decision == Decision.AUTO:
                auto_count += 1
            elif decision == Decision.ESCALATE:
                escalate_count += 1
            elif decision == Decision.BLOCK:
                block_count += 1

            # Audit decision (up to 1,000 individual records to prevent event flood on big tables)
            if len(decisions) <= 1000:
                audit_ledger.record(
                    decision.value,
                    "system",
                    dataset_id,
                    decision_id=decision_record["decision_id"],
                    details={
                        "row_id": row_id,
                        "column": column,
                        "belief_error": fusion_result["belief_error"],
                        "conflict": fusion_result["conflict"],
                    },
                )

        if len(decisions) > 1000:
            audit_ledger.record(
                "BATCH_DECISIONS",
                "system",
                dataset_id,
                details={
                    "total_decisions": len(decisions),
                    "auto_count": auto_count,
                    "escalate_count": escalate_count,
                    "block_count": block_count,
                },
            )

        result["decisions"] = decisions

        # ── Summary ──
        elapsed = time.time() - start_time
        result["summary"] = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "total_evidence": len(all_evidence),
            "total_decisions": len(decisions),
            "auto_count": auto_count,
            "escalate_count": escalate_count,
            "block_count": block_count,
            "automation_rate": round(auto_count / max(len(decisions), 1), 4),
            "escalation_rate": round(escalate_count / max(len(decisions), 1), 4),
            "elapsed_seconds": round(elapsed, 2),
        }

        # ── Assistant Narrative & Reasoning Report ──
        try:
            result["assistant_report"] = generate_assistant_report(
                filename=metadata.get("original_filename", "dataset.csv"),
                profile=result.get("profile"),
                decisions=decisions,
                evidence=result.get("evidence", []),
                summary=result["summary"],
            )
        except Exception as e:
            logger.warning(f"Failed to generate assistant report: {e}")
            result["assistant_report"] = None

        result["status"] = "COMPLETED"

        logger.info(
            f"Pipeline complete: {len(decisions)} decisions "
            f"(AUTO={auto_count}, ESCALATE={escalate_count}, BLOCK={block_count}) "
            f"in {elapsed:.1f}s"
        )

        return result


# Singleton
pipeline = AnalysisPipeline()
