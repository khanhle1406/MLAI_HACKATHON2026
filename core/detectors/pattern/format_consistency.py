"""Pattern-based detectors: format consistency, whitespace, date format.

Adapted from AutoCSV-LED P1 (pattern_rarity) and extended with
format-specific detectors for competition verify cases.
"""

from __future__ import annotations

import re

import polars as pl

from core.detectors.base import BaseDetector
from core.evidence.schema import Claim, EvidenceItem, SourceType

# ── Character class shape (from AutoCSV-LED) ──
_UP = re.compile(r"[A-Z]+")
_LO = re.compile(r"[a-z]+")
_DG = re.compile(r"[0-9]+")
_WS = re.compile(r"\s+")

PATTERN_RARE_SHARE = 0.05  # AutoCSV-LED hyperparameter


def _shape(v: str) -> str:
    """Character-class shape: 'Birmingham 35235' -> 'Aa 9'."""
    s = _UP.sub("A", v)
    s = _LO.sub("a", s)
    s = _DG.sub("9", s)
    return _WS.sub(" ", s)


class PatternRarityDetector(BaseDetector):
    """Detect values with rare syntactic patterns.

    Direct adaptation of AutoCSV-LED P1: pattern_rarity profiler.
    A cell whose character-class shape covers < 5% of its column
    is flagged as potentially erroneous.
    """

    name = "pattern_rarity_detector"
    description = "Detects values with rare syntactic patterns (AutoCSV-LED P1)"
    source_type = "deterministic"
    family = "syntax"

    def _detect_column(self, df: pl.DataFrame, column: str) -> list[EvidenceItem]:
        evidence: list[EvidenceItem] = []
        series = df[column]

        if series.dtype not in (pl.Utf8, pl.String):
            return evidence

        values = series.drop_nulls().cast(pl.Utf8).to_list()
        if len(values) < 5:
            return evidence

        # Compute shapes
        shapes = [_shape(str(v)) for v in values]
        from collections import Counter
        shape_counts = Counter(shapes)
        n = len(shapes)

        # Dominant pattern share (column regularity)
        dominant_share = shape_counts.most_common(1)[0][1] / n

        # Find rare patterns
        row_idx = 0
        for i in range(len(df)):
            val = series[i]
            if val is None:
                continue

            val_str = str(val)
            s = _shape(val_str)
            share = shape_counts[s] / n

            if share < PATTERN_RARE_SHARE:
                score = dominant_share * min(1.0, 1.0 - share / PATTERN_RARE_SHARE)
                evidence.append(EvidenceItem(
                    row_id=i,
                    column=column,
                    detector=self.name,
                    source_type=SourceType.DETERMINISTIC,
                    claim=Claim.POSSIBLE_ERROR,
                    score=round(min(score, 1.0), 4),
                    support={
                        "observed_value": val_str,
                        "observed_pattern": s,
                        "pattern_share": round(share, 4),
                        "reason_codes": ["rare_pattern"],
                    },
                    reference_verified=True,
                    counterevidence=[
                        "Value may be a valid outlier or special case",
                        f"Pattern '{s}' appears in {share*100:.1f}% of values",
                    ],
                ))

        return evidence


class WhitespaceDetector(BaseDetector):
    """Detect leading/trailing whitespace — candidate for AUTO-FIX.

    Competition Verify V1: whitespace normalization.
    """

    name = "whitespace_detector"
    description = "Detects leading/trailing whitespace in string values"
    source_type = "deterministic"
    family = "syntax"

    def _detect_column(self, df: pl.DataFrame, column: str) -> list[EvidenceItem]:
        evidence: list[EvidenceItem] = []
        series = df[column]

        if series.dtype not in (pl.Utf8, pl.String):
            return evidence

        for i in range(len(df)):
            val = series[i]
            if val is None:
                continue
            val_str = str(val)
            stripped = val_str.strip()
            if val_str != stripped and len(stripped) > 0:
                evidence.append(EvidenceItem(
                    row_id=i,
                    column=column,
                    detector=self.name,
                    source_type=SourceType.DETERMINISTIC,
                    claim=Claim.POSSIBLE_ERROR,
                    score=0.95,
                    support={
                        "observed_value": val_str,
                        "expected_value": stripped,
                        "reason_codes": ["leading_trailing_whitespace"],
                        "action": "normalize_whitespace",
                        "repair_deterministic": True,
                        "repair_reversible": True,
                    },
                    reference_verified=True,
                    counterevidence=[
                        "Whitespace may be intentional in some rare formats",
                    ],
                ))

        return evidence


class DateFormatDetector(BaseDetector):
    """Detect inconsistent date formats — candidate for AUTO-FIX.

    Competition Verify V2: date format normalization.
    """

    name = "date_format_detector"
    description = "Detects inconsistent date formats in columns"
    source_type = "deterministic"
    family = "syntax"

    DATE_PATTERNS = [
        (re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$"), "DD/MM/YYYY or MM/DD/YYYY"),
        (re.compile(r"^\d{1,2}-\d{1,2}-\d{4}$"), "DD-MM-YYYY"),
        (re.compile(r"^\d{1,2}\.\d{1,2}\.\d{4}$"), "DD.MM.YYYY"),
        (re.compile(r"^\d{4}-\d{2}-\d{2}$"), "YYYY-MM-DD (ISO)"),
        (re.compile(r"^\d{4}/\d{2}/\d{2}$"), "YYYY/MM/DD"),
        (re.compile(r"^\d{1,2}/\d{1,2}/\d{2}$"), "DD/MM/YY"),
    ]
    ISO_FORMAT = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    def _detect_column(self, df: pl.DataFrame, column: str) -> list[EvidenceItem]:
        evidence: list[EvidenceItem] = []
        series = df[column]

        if series.dtype not in (pl.Utf8, pl.String):
            return evidence

        values = series.drop_nulls().cast(pl.Utf8).to_list()
        if len(values) < 3:
            return evidence

        # Count formats
        from collections import Counter
        format_counts: Counter = Counter()
        value_formats: dict[int, str] = {}

        for i in range(len(df)):
            val = series[i]
            if val is None:
                continue
            val_str = str(val).strip()
            for pattern, fmt_name in self.DATE_PATTERNS:
                if pattern.match(val_str):
                    format_counts[fmt_name] += 1
                    value_formats[i] = fmt_name
                    break

        if len(format_counts) < 2:
            return evidence  # All same format or no dates

        # Most common format is the "expected" one
        dominant_format, dominant_count = format_counts.most_common(1)[0]
        total_dates = sum(format_counts.values())

        for i, fmt in value_formats.items():
            if fmt != dominant_format:
                val_str = str(series[i]).strip()
                evidence.append(EvidenceItem(
                    row_id=i,
                    column=column,
                    detector=self.name,
                    source_type=SourceType.DETERMINISTIC,
                    claim=Claim.POSSIBLE_ERROR,
                    score=round(dominant_count / total_dates, 4),
                    support={
                        "observed_value": val_str,
                        "observed_format": fmt,
                        "expected_format": dominant_format,
                        "reason_codes": ["inconsistent_date_format"],
                        "action": "normalize_date",
                        "repair_deterministic": True,
                        "repair_reversible": True,
                    },
                    reference_verified=True,
                    counterevidence=[
                        f"Format '{fmt}' may be intentional for this subset",
                        "Some date formats are ambiguous (DD/MM vs MM/DD)",
                    ],
                ))

        return evidence
