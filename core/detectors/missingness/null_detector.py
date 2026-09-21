"""Missingness detectors: null values, disguised nulls, placeholders.

Adapted from AutoCSV-LED P2 (missing_tokens).
"""

from __future__ import annotations

import polars as pl

from core.detectors.base import BaseDetector
from core.evidence.schema import Claim, EvidenceItem, SourceType

NULL_TOKENS = {"", "n/a", "na", "null", "none", "nan", "-", "--", "?", "#n/a", "missing", "unknown", "n.a.", "n/d"}


class NullDetector(BaseDetector):
    """Detect explicit null/missing values."""

    name = "null_detector"
    description = "Detects null/missing values in columns"
    source_type = "deterministic"
    family = "syntax"

    def _detect_column(self, df: pl.DataFrame, column: str) -> list[EvidenceItem]:
        evidence: list[EvidenceItem] = []
        series = df[column]
        null_mask = series.is_null()

        for row_idx in null_mask.arg_true().to_list():
            evidence.append(EvidenceItem(
                row_id=row_idx,
                column=column,
                detector=self.name,
                source_type=SourceType.DETERMINISTIC,
                claim=Claim.POSSIBLE_ERROR,
                score=0.8,
                support={
                    "observed_value": None,
                    "reason_codes": ["explicit_null"],
                },
                reference_verified=True,
                counterevidence=["Column may allow null values (optional field)"],
            ))

        return evidence


class DisguisedNullDetector(BaseDetector):
    """Detect disguised null values (e.g., 'N/A', '-', '?').

    Adapted from AutoCSV-LED P2: missing_tokens profiler.
    """

    name = "disguised_null_detector"
    description = "Detects disguised null values using known null tokens"
    source_type = "deterministic"
    family = "syntax"

    def _detect_column(self, df: pl.DataFrame, column: str) -> list[EvidenceItem]:
        evidence: list[EvidenceItem] = []
        series = df[column]

        if series.dtype not in (pl.Utf8, pl.String):
            return evidence

        non_null = series.drop_nulls()
        if len(non_null) == 0:
            return evidence

        # Calculate fraction of disguised nulls
        str_series = non_null.cast(pl.Utf8)
        lower_stripped = str_series.str.strip_chars().str.to_lowercase()

        for row_idx in range(len(df)):
            val = series[row_idx]
            if val is None:
                continue
            val_str = str(val).strip().lower()
            if val_str in NULL_TOKENS:
                # Calculate evidence strength based on how rare the null token is
                null_frac = sum(
                    1 for v in lower_stripped.to_list()
                    if v in NULL_TOKENS
                ) / len(lower_stripped)

                # If most values are null tokens, this is "normal" — skip
                if null_frac > 0.5:
                    continue

                score = min(1.0, 1.0 - null_frac)

                evidence.append(EvidenceItem(
                    row_id=row_idx,
                    column=column,
                    detector=self.name,
                    source_type=SourceType.DETERMINISTIC,
                    claim=Claim.POSSIBLE_ERROR,
                    score=round(score, 4),
                    support={
                        "observed_value": str(val),
                        "reason_codes": ["disguised_null"],
                        "null_token_match": val_str,
                        "null_fraction": round(null_frac, 4),
                    },
                    reference_verified=True,
                    counterevidence=[
                        "Value may be intentional (e.g., '-' for not applicable)",
                        f"Null tokens represent {null_frac*100:.1f}% of column",
                    ],
                ))

        return evidence
