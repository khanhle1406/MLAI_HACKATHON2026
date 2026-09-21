"""Statistical detectors: outlier detection using IQR and Z-score.

Detects values that are statistically anomalous within their column.
Used for Verify V4: factual uncertainty escalation.
"""

from __future__ import annotations

import logging

import numpy as np
import polars as pl

from core.detectors.base import BaseDetector
from core.evidence.schema import Claim, EvidenceItem, SourceType

logger = logging.getLogger(__name__)

IQR_MULTIPLIER = 1.5
ZSCORE_THRESHOLD = 3.0
MIN_NUMERIC_VALUES = 5


class OutlierDetector(BaseDetector):
    """Detect statistical outliers using IQR method.

    For Verify V4: salary = 50,000,000 when others are ~15-18M
    should be flagged as a statistical anomaly → ESCALATE.
    """

    name = "outlier_detector"
    description = "Detects statistical outliers using IQR and Z-score"
    source_type = "statistical"
    family = "value"

    def _detect_column(self, df: pl.DataFrame, column: str) -> list[EvidenceItem]:
        evidence: list[EvidenceItem] = []
        series = df[column]

        # Only apply to numeric columns
        if series.dtype not in (
            pl.Int8, pl.Int16, pl.Int32, pl.Int64,
            pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64,
            pl.Float32, pl.Float64,
        ):
            return evidence

        non_null = series.drop_nulls()
        if len(non_null) < MIN_NUMERIC_VALUES:
            return evidence

        values = non_null.to_numpy().astype(float)
        n = len(values)

        # IQR method
        q1 = float(np.percentile(values, 25))
        q3 = float(np.percentile(values, 75))
        iqr = q3 - q1

        if iqr == 0:
            return evidence

        lower_bound = q1 - IQR_MULTIPLIER * iqr
        upper_bound = q3 + IQR_MULTIPLIER * iqr

        # Z-score
        mean = float(np.mean(values))
        std = float(np.std(values))

        for i in range(len(df)):
            val = series[i]
            if val is None:
                continue

            val_f = float(val)
            is_iqr_outlier = val_f < lower_bound or val_f > upper_bound

            z_score = abs(val_f - mean) / std if std > 0 else 0.0
            is_zscore_outlier = z_score > ZSCORE_THRESHOLD

            if is_iqr_outlier or is_zscore_outlier:
                # Score based on how extreme the outlier is
                if std > 0:
                    score = min(1.0, z_score / (ZSCORE_THRESHOLD * 2))
                else:
                    score = 0.7

                evidence.append(EvidenceItem(
                    row_id=i,
                    column=column,
                    detector=self.name,
                    source_type=SourceType.STATISTICAL,
                    claim=Claim.POSSIBLE_ERROR,
                    score=round(score, 4),
                    support={
                        "observed_value": str(val),
                        "mean": round(mean, 2),
                        "std": round(std, 2),
                        "z_score": round(z_score, 2),
                        "iqr_bounds": [round(lower_bound, 2), round(upper_bound, 2)],
                        "q1": round(q1, 2),
                        "q3": round(q3, 2),
                        "reason_codes": [
                            "iqr_outlier" if is_iqr_outlier else None,
                            "zscore_outlier" if is_zscore_outlier else None,
                        ],
                    },
                    reference_verified=True,  # Deterministic computation
                    counterevidence=[
                        "Outlier detection is statistical — the value may be legitimately extreme",
                        f"Value is {z_score:.1f} standard deviations from mean ({mean:.0f})",
                        "Some domains naturally have high variance",
                    ],
                ))

        return evidence
