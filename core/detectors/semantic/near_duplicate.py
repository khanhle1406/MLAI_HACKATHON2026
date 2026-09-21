"""Near-duplicate / typo detector using fuzzy string matching.

Adapted from AutoCSV-LED Profiler P3 — detects values that are
suspiciously similar (likely typos or near-duplicates).
"""

from __future__ import annotations

import logging
from collections import Counter

import polars as pl

from core.detectors.base import BaseDetector
from core.evidence.schema import Claim, EvidenceItem, SourceType

logger = logging.getLogger(__name__)

MIN_VALUES_FOR_CHECK = 5
SIMILARITY_THRESHOLD = 0.85
MIN_FREQUENCY_FOR_CANONICAL = 2


class NearDuplicateDetector(BaseDetector):
    """Detect near-duplicate values that are likely typos.

    Uses Levenshtein distance via rapidfuzz for efficient fuzzy matching.
    Example: "Ho Chi Minh" vs "Ho CHi Minh" → likely typo.
    """

    name = "near_duplicate_detector"
    description = "Detects near-duplicate values (likely typos)"
    source_type = "deterministic"
    family = "value"

    def _detect_column(self, df: pl.DataFrame, column: str) -> list[EvidenceItem]:
        evidence: list[EvidenceItem] = []
        series = df[column]

        # Only check string columns
        if series.dtype != pl.Utf8:
            return evidence

        non_null = series.drop_nulls()
        if len(non_null) < MIN_VALUES_FOR_CHECK:
            return evidence

        values = non_null.to_list()
        # Count frequencies
        freq = Counter(values)
        unique_values = list(freq.keys())

        if len(unique_values) < 2 or len(unique_values) > 500:
            return evidence

        try:
            from rapidfuzz import fuzz
        except ImportError:
            logger.warning("rapidfuzz not installed, skipping near-duplicate detection")
            return evidence

        # Find canonical values (most frequent variants)
        canonical = [v for v, c in freq.items() if c >= MIN_FREQUENCY_FOR_CANONICAL]
        if not canonical:
            # Use all values with freq == 1 as candidates
            canonical = [v for v, c in freq.items() if c > 1]
            if not canonical:
                return evidence

        # Check each rare value against canonical values
        for val, count in freq.items():
            if count >= MIN_FREQUENCY_FOR_CANONICAL:
                continue  # Skip canonical values themselves

            for canon in canonical:
                if val == canon:
                    continue

                ratio = fuzz.ratio(val.lower(), canon.lower()) / 100.0
                if ratio >= SIMILARITY_THRESHOLD and ratio < 1.0:
                    # Found near-duplicate — likely typo
                    score = ratio  # Higher similarity = higher confidence it's a typo

                    # Find all row indices with this value
                    for i in range(len(df)):
                        if series[i] == val:
                            evidence.append(EvidenceItem(
                                row_id=i,
                                column=column,
                                detector=self.name,
                                source_type=SourceType.DETERMINISTIC,
                                claim=Claim.POSSIBLE_ERROR,
                                score=round(score, 4),
                                support={
                                    "observed_value": val,
                                    "expected_value": canon,
                                    "similarity": round(ratio, 4),
                                    "canonical_frequency": freq[canon],
                                    "reason_codes": ["near_duplicate", "possible_typo"],
                                    "action": "normalize",
                                    "repair_deterministic": True,
                                    "repair_reversible": True,
                                },
                                reference_verified=True,
                                counterevidence=[
                                    f"'{val}' might be intentionally different from '{canon}'",
                                    "Similarity check may produce false positives",
                                ],
                            ))
                    break  # Only match with closest canonical

        return evidence
