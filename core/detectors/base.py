"""Base detector abstract class.

Every detector in DataGuard extends this class and produces
EvidenceItem instances. Detectors are organized in tiers:

  Tier 0: Deterministic (structural, type, format, pattern)
  Tier 1: Statistical (outlier, distribution)
  Tier 2: Relational (FD, duplicate, entity)
  Tier 3: Semantic (LLM-based — separate module)

INVARIANT: Detector failure is non-fatal. A failed detector
produces no evidence (fail-open) and logs a warning.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import polars as pl

from core.evidence.schema import EvidenceItem

logger = logging.getLogger(__name__)


class BaseDetector(ABC):
    """Abstract base class for all data quality detectors."""

    name: str = "base"
    description: str = ""
    source_type: str = "deterministic"  # deterministic, statistical, relational, semantic
    family: str = "syntax"              # For D-S fusion grouping

    def detect(self, df: pl.DataFrame, column: str | None = None) -> list[EvidenceItem]:
        """Run detection with error handling.

        Args:
            df: Input DataFrame.
            column: Optional column to focus on. If None, detect across all columns.

        Returns:
            List of EvidenceItem instances.
        """
        try:
            if column:
                return self._detect_column(df, column)
            else:
                return self._detect_all(df)
        except Exception as e:
            logger.warning(f"Detector '{self.name}' failed: {e}")
            return []  # Fail open — don't block the pipeline

    def _detect_all(self, df: pl.DataFrame) -> list[EvidenceItem]:
        """Detect across all columns. Override for table-level detectors."""
        evidence: list[EvidenceItem] = []
        for col in df.columns:
            evidence.extend(self._detect_column(df, col))
        return evidence

    @abstractmethod
    def _detect_column(self, df: pl.DataFrame, column: str) -> list[EvidenceItem]:
        """Detect issues in a single column. Must be implemented by subclasses."""
        ...
