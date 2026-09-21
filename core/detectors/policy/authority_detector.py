"""Policy detectors: detect data requiring special authority or policy.

Handles Verify V5: financial/sensitive data that requires human authority
for any modifications.
"""

from __future__ import annotations

import logging
import re

import polars as pl

from core.detectors.base import BaseDetector
from core.evidence.schema import Claim, EvidenceItem, SourceType

logger = logging.getLogger(__name__)

# Keywords indicating financial/sensitive data
FINANCIAL_KEYWORDS = {
    "amount", "price", "cost", "salary", "income", "revenue", "profit",
    "balance", "total", "payment", "transaction", "refund", "invoice",
    "credit", "debit", "fee", "charge", "tax", "budget", "expenditure",
}

SENSITIVE_COLUMN_KEYWORDS = {
    "ssn", "password", "secret", "token", "private_key",
    "credit_card", "account_number", "bank",
}

SENSITIVE_TABLE_KEYWORDS = {
    "transaction", "payment", "invoice", "salary", "payroll",
    "financial", "accounting", "billing", "ledger",
}


class HighValueDataDetector(BaseDetector):
    """Detect high-value/financial data that requires authority for changes.

    Verify V5: any action on financial transaction data should ESCALATE
    because the AI lacks authority to modify financial records.
    """

    name = "high_value_data_detector"
    description = "Detects financial/sensitive data requiring authority escalation"
    source_type = "deterministic"
    family = "policy"

    def _detect_all(self, df: pl.DataFrame) -> list[EvidenceItem]:
        """Detect at table level — check if table contains high-value data."""
        evidence: list[EvidenceItem] = []

        # Check column names for financial/sensitive indicators
        financial_columns: list[str] = []
        sensitive_columns: list[str] = []

        for col in df.columns:
            col_lower = col.lower().strip()
            for keyword in FINANCIAL_KEYWORDS:
                if keyword in col_lower:
                    financial_columns.append(col)
                    break
            for keyword in SENSITIVE_COLUMN_KEYWORDS:
                if keyword in col_lower:
                    sensitive_columns.append(col)
                    break

        # Check if table name (from columns) suggests financial data
        all_cols_lower = " ".join(c.lower() for c in df.columns)
        is_financial_table = any(k in all_cols_lower for k in SENSITIVE_TABLE_KEYWORDS)

        if not financial_columns and not sensitive_columns and not is_financial_table:
            return evidence

        # Flag every row in financial columns as needing authority
        target_columns = financial_columns + sensitive_columns
        if not target_columns and is_financial_table:
            # If table is financial but no specific column, flag first numeric
            for col in df.columns:
                if df[col].dtype in (
                    pl.Int8, pl.Int16, pl.Int32, pl.Int64,
                    pl.Float32, pl.Float64,
                ):
                    target_columns.append(col)

        for col in target_columns:
            series = df[col]
            for i in range(len(df)):
                val = series[i]
                if val is None:
                    continue

                evidence.append(EvidenceItem(
                    row_id=i,
                    column=col,
                    detector=self.name,
                    source_type=SourceType.DETERMINISTIC,
                    claim=Claim.UNCERTAIN,
                    score=0.6,
                    support={
                        "observed_value": str(val),
                        "reason_codes": ["high_value_data", "requires_authority"],
                        "action": "verify_authority",
                        "repair_deterministic": False,
                        "repair_reversible": False,
                        "required_authority": 2,
                    },
                    reference_verified=True,
                    counterevidence=[
                        "Column may not contain actual financial data",
                        "Value may be a test/sample value",
                    ],
                ))

        return evidence

    def _detect_column(self, df: pl.DataFrame, column: str) -> list[EvidenceItem]:
        return []
