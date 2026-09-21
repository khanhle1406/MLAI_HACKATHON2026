"""Relational detectors: duplicate keys, functional dependency violations.

Duplicate key detection: Verify V3.
FD violations: adapted from AutoCSV-LED P4 (fd_violations).
"""

from __future__ import annotations

import logging
from collections import Counter

import polars as pl

from core.detectors.base import BaseDetector
from core.evidence.schema import Claim, EvidenceItem, SourceType

logger = logging.getLogger(__name__)

FD_MIN_CONF = 0.90
FD_MIN_GROUP = 3
NULL_TOKENS = {"", "n/a", "na", "null", "none", "nan", "-", "--", "?", "#n/a"}


class DuplicateKeyDetector(BaseDetector):
    """Detect duplicate values in columns that appear to be primary keys.

    Competition Verify V3: duplicate detection.
    """

    name = "duplicate_key_detector"
    description = "Detects duplicate values in key-like columns"
    source_type = "deterministic"
    family = "value"

    def _detect_all(self, df: pl.DataFrame) -> list[EvidenceItem]:
        """Detect duplicates across all potential key columns."""
        evidence: list[EvidenceItem] = []

        for col in df.columns:
            series = df[col]
            n = len(series)
            n_unique = series.n_unique()

            # Check column name hints
            col_lower = col.lower()
            is_key_hint = any(k in col_lower for k in ("id", "key", "code", "number", "mã", "stt"))

            # For key-named columns, lower threshold; otherwise need >90% unique
            min_unique_rate = 0.5 if is_key_hint else 0.9
            if n_unique < n * min_unique_rate or n < 3:
                continue

            if n_unique == n and not is_key_hint:
                continue  # Already fully unique, no duplicates

            if n_unique < n:
                # Find actual duplicates
                dup_mask = series.is_duplicated()
                dup_values = series.filter(dup_mask).unique().to_list()

                for dup_val in dup_values[:50]:  # Limit to first 50
                    dup_rows = [i for i in range(n) if series[i] == dup_val]
                    for row_idx in dup_rows:
                        evidence.append(EvidenceItem(
                            row_id=row_idx,
                            column=col,
                            detector=self.name,
                            source_type=SourceType.DETERMINISTIC,
                            claim=Claim.POSSIBLE_ERROR,
                            score=0.9,
                            support={
                                "observed_value": str(dup_val),
                                "duplicate_count": len(dup_rows),
                                "duplicate_rows": dup_rows[:10],
                                "reason_codes": ["duplicate_key"],
                            },
                            reference_verified=True,
                            counterevidence=[
                                "Column may not be a primary key",
                                "Duplicate values may be intentional (e.g., foreign key)",
                            ],
                        ))

        return evidence

    def _detect_column(self, df: pl.DataFrame, column: str) -> list[EvidenceItem]:
        """Not used — this detector works at table level."""
        return []


class FDViolationDetector(BaseDetector):
    """Detect functional dependency violations.

    Adapted from AutoCSV-LED P4: fd_violations profiler.
    Mines approximate FDs (X -> Y with |X|=1) and flags violations.
    """

    name = "fd_violation_detector"
    description = "Detects functional dependency violations (AutoCSV-LED P4)"
    source_type = "deterministic"
    family = "value"

    def _detect_all(self, df: pl.DataFrame) -> list[EvidenceItem]:
        """Mine FDs and detect violations at table level."""
        evidence: list[EvidenceItem] = []

        # Convert to pandas for AutoCSV-LED compatibility
        pdf = df.to_pandas()
        n = len(pdf)

        if n < FD_MIN_GROUP:
            return evidence

        # Mine approximate FDs
        fds = self._mine_fds(pdf)
        logger.info(f"FDViolationDetector: mined {len(fds)} FDs")

        # Detect violations
        for x_col, y_col, conf in fds:
            violations = self._find_violations(pdf, x_col, y_col)
            for row_idx, val, expected_val, group_size in violations:
                evidence.append(EvidenceItem(
                    row_id=row_idx,
                    column=y_col,
                    detector=self.name,
                    source_type=SourceType.DETERMINISTIC,
                    claim=Claim.POSSIBLE_ERROR,
                    score=round(conf * 0.9, 4),
                    support={
                        "observed_value": str(val),
                        "expected_value": str(expected_val),
                        "fd_rule": f"{x_col} -> {y_col}",
                        "fd_confidence": round(conf, 4),
                        "group_size": group_size,
                        "reason_codes": ["fd_violation"],
                    },
                    reference_verified=True,
                    counterevidence=[
                        f"FD {x_col}->{y_col} is approximate (conf={conf:.2f}), not proven",
                        "The minority value may be the correct one",
                        "Data may have legitimate variations",
                    ],
                ))

        return evidence

    def _mine_fds(self, df) -> list[tuple[str, str, float]]:
        """Mine approximate single-column FDs. From AutoCSV-LED."""
        import pandas as pd
        n = len(df)
        nun = df.nunique()
        fds = []

        for x in df.columns:
            if nun[x] <= 1 or nun[x] >= 0.9 * n:
                continue
            sizes = df.groupby(x, sort=False)[x].transform("size")
            big = sizes >= FD_MIN_GROUP
            if big.sum() < 0.3 * n:
                continue
            sub = df[big]

            for y in df.columns:
                if y == x or nun[y] <= 1:
                    continue
                ok = ~sub[y].astype(str).str.strip().str.lower().isin(NULL_TOKENS)
                if ok.sum() < 0.3 * n:
                    continue
                try:
                    mode_cnt = sub[ok].groupby(x, sort=False)[y].agg(
                        lambda s: s.value_counts().iloc[0]
                    )
                    conf = mode_cnt.sum() / ok.sum()
                    if conf >= FD_MIN_CONF and df[y].value_counts(normalize=True).iloc[0] < 0.9:
                        fds.append((x, y, float(conf)))
                except Exception:
                    continue

        return fds

    def _find_violations(self, df, x_col, y_col) -> list[tuple[int, str, str, int]]:
        """Find rows that violate the FD X -> Y."""
        violations = []
        groups = df.groupby(x_col, sort=False)

        for x_val, group in groups:
            if len(group) < FD_MIN_GROUP:
                continue
            y_values = group[y_col].astype(str).str.strip()
            y_clean = y_values[~y_values.str.lower().isin(NULL_TOKENS)]
            if len(y_clean) < 2:
                continue

            mode_val = y_clean.mode()
            if len(mode_val) == 0:
                continue
            mode_val = mode_val.iloc[0]
            mode_count = (y_clean == mode_val).sum()

            for idx, val in y_clean.items():
                if val != mode_val and mode_count > (y_clean == val).sum():
                    violations.append((int(idx), str(val), str(mode_val), len(group)))

        return violations[:100]  # Limit

    def _detect_column(self, df: pl.DataFrame, column: str) -> list[EvidenceItem]:
        return []
