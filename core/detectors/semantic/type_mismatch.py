"""Type mismatch detector: finds values that don't match column's dominant type.

Example: column inferred as 'integer' but row 5 has "abc" or "12.5".
"""

from __future__ import annotations

import logging
import re

import polars as pl

from core.detectors.base import BaseDetector
from core.evidence.schema import Claim, EvidenceItem, SourceType

logger = logging.getLogger(__name__)


class TypeMismatchDetector(BaseDetector):
    """Detect values that don't match the column's dominant data type."""

    name = "type_mismatch_detector"
    description = "Detects values inconsistent with column's dominant type"
    source_type = "deterministic"
    family = "syntax"

    INTEGER_RE = re.compile(r"^-?\d+$")
    FLOAT_RE = re.compile(r"^-?\d+\.?\d*$")

    def _detect_column(self, df: pl.DataFrame, column: str) -> list[EvidenceItem]:
        evidence: list[EvidenceItem] = []
        series = df[column]

        # Only check string columns
        if series.dtype != pl.Utf8:
            return evidence

        non_null = series.drop_nulls()
        if len(non_null) < 5:
            return evidence

        values = non_null.to_list()

        # Determine dominant type
        int_count = sum(1 for v in values if self.INTEGER_RE.match(str(v).strip()))
        float_count = sum(1 for v in values if self.FLOAT_RE.match(str(v).strip()))
        total = len(values)

        dominant_type = None
        if int_count / total > 0.8:
            dominant_type = "integer"
        elif float_count / total > 0.8:
            dominant_type = "numeric"

        if not dominant_type:
            return evidence

        # Find mismatches
        for i in range(len(df)):
            val = series[i]
            if val is None:
                continue

            val_str = str(val).strip()
            if not val_str:
                continue

            is_match = False
            if dominant_type == "integer":
                is_match = bool(self.INTEGER_RE.match(val_str))
            elif dominant_type == "numeric":
                is_match = bool(self.FLOAT_RE.match(val_str))

            if not is_match:
                evidence.append(EvidenceItem(
                    row_id=i,
                    column=column,
                    detector=self.name,
                    source_type=SourceType.DETERMINISTIC,
                    claim=Claim.POSSIBLE_ERROR,
                    score=0.85,
                    support={
                        "observed_value": val_str,
                        "expected_type": dominant_type,
                        "reason_codes": ["type_mismatch"],
                        "action": "flag_for_review",
                    },
                    reference_verified=True,
                    counterevidence=[
                        "Value might be a valid special case (e.g., 'N/A', 'TBD')",
                        f"Column may not be purely {dominant_type}",
                    ],
                ))

        return evidence
