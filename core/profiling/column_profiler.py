"""Column profiling engine — deterministic, no LLM.

Produces ColumnProfile for each column: type inference, statistics,
pattern distribution, PII detection, semantic type guessing.
Uses Polars for performance.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import numpy as np
import polars as pl

from core.evidence.schema import ColumnProfile

logger = logging.getLogger(__name__)

# ── Semantic Type Patterns ──
SEMANTIC_PATTERNS: dict[str, re.Pattern] = {
    "email": re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
    "phone": re.compile(r"^[\+]?[\d\s\-\(\)\.]{7,20}$"),
    "url": re.compile(r"^https?://[^\s]+$"),
    "ip_address": re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"),
    "date_iso": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "date_dmy": re.compile(r"^\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}$"),
    "currency": re.compile(r"^[\$€£¥₫]\s?[\d,]+\.?\d*$"),
    "percentage": re.compile(r"^\d+\.?\d*\s?%$"),
    "uuid": re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I),
    "zipcode_us": re.compile(r"^\d{5}(-\d{4})?$"),
    "ssn": re.compile(r"^\d{3}-\d{2}-\d{4}$"),
    "credit_card": re.compile(r"^\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}$"),
}

# ── PII Patterns ──
PII_PATTERNS: dict[str, re.Pattern] = {
    "email": SEMANTIC_PATTERNS["email"],
    "phone": SEMANTIC_PATTERNS["phone"],
    "ssn": SEMANTIC_PATTERNS["ssn"],
    "credit_card": SEMANTIC_PATTERNS["credit_card"],
}

PII_COLUMN_KEYWORDS = {
    "name", "first_name", "last_name", "fullname", "full_name",
    "email", "phone", "mobile", "address", "street", "ssn",
    "social_security", "passport", "license", "dob", "birth",
    "salary", "income", "credit_card", "card_number", "password",
}

# ── Null tokens ──
NULL_TOKENS = {"", "n/a", "na", "null", "none", "nan", "-", "--", "?", "#n/a", "missing", "unknown", "n.a."}

# ── Character class shape (from AutoCSV-LED) ──
_UP = re.compile(r"[A-Z]+")
_LO = re.compile(r"[a-z]+")
_DG = re.compile(r"[0-9]+")
_WS = re.compile(r"\s+")


def _shape(v: str) -> str:
    """Character-class shape: 'Birmingham 35235' -> 'Aa 9'."""
    s = _UP.sub("A", v)
    s = _LO.sub("a", s)
    s = _DG.sub("9", s)
    return _WS.sub(" ", s)


def infer_observed_type(series: pl.Series) -> str:
    """Infer the observed data type of a column."""
    dtype = series.dtype
    if dtype in (pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64):
        return "integer"
    elif dtype in (pl.Float32, pl.Float64):
        return "float"
    elif dtype == pl.Boolean:
        return "boolean"
    elif dtype in (pl.Date, pl.Datetime, pl.Time):
        return "datetime"
    elif dtype == pl.Utf8 or dtype == pl.String:
        return "string"
    else:
        return str(dtype)


def infer_semantic_type(series: pl.Series, column_name: str) -> tuple[str | None, float]:
    """Infer semantic type using regex patterns and column name heuristics.

    Returns:
        Tuple of (semantic_type, confidence).
    """
    col_lower = column_name.lower().strip()

    # Column name heuristics
    name_hints: dict[str, str] = {
        "email": "email", "mail": "email",
        "phone": "phone", "tel": "phone", "mobile": "phone",
        "url": "url", "website": "url", "link": "url",
        "date": "date", "created": "date", "updated": "date",
        "birth": "date", "dob": "date",
        "price": "currency", "cost": "currency", "amount": "currency",
        "salary": "currency", "income": "currency",
        "zip": "zipcode", "postal": "zipcode",
        "ip": "ip_address",
        "id": "identifier", "uuid": "identifier", "key": "identifier",
    }

    for keyword, sem_type in name_hints.items():
        if keyword in col_lower:
            return sem_type, 0.7

    # Pattern matching on sample values
    if series.dtype not in (pl.Utf8, pl.String):
        return None, 0.0

    non_null = series.drop_nulls().cast(pl.Utf8)
    if len(non_null) == 0:
        return None, 0.0

    sample_size = min(200, len(non_null))
    sample = non_null.sample(sample_size, seed=42) if len(non_null) > sample_size else non_null

    best_type = None
    best_score = 0.0

    for sem_type, pattern in SEMANTIC_PATTERNS.items():
        matches = sum(1 for v in sample.to_list() if pattern.match(str(v)))
        match_rate = matches / len(sample) if len(sample) > 0 else 0.0
        if match_rate > best_score and match_rate >= 0.5:
            best_type = sem_type
            best_score = match_rate

    return best_type, best_score


def detect_pii_likelihood(series: pl.Series, column_name: str) -> float:
    """Estimate PII likelihood based on column name and value patterns."""
    likelihood = 0.0
    col_lower = column_name.lower().strip()

    # Column name check
    for keyword in PII_COLUMN_KEYWORDS:
        if keyword in col_lower:
            likelihood = max(likelihood, 0.6)
            break

    # Pattern check on values
    if series.dtype in (pl.Utf8, pl.String):
        non_null = series.drop_nulls().cast(pl.Utf8)
        if len(non_null) > 0:
            sample_size = min(100, len(non_null))
            sample = non_null.sample(sample_size, seed=42) if len(non_null) > sample_size else non_null
            for pii_type, pattern in PII_PATTERNS.items():
                matches = sum(1 for v in sample.to_list() if pattern.match(str(v)))
                match_rate = matches / len(sample) if len(sample) > 0 else 0.0
                if match_rate >= 0.3:
                    likelihood = max(likelihood, 0.5 + match_rate * 0.5)

    return min(likelihood, 1.0)


def compute_statistics(series: pl.Series) -> dict[str, Any]:
    """Compute column statistics using Polars."""
    stats: dict[str, Any] = {}
    dtype = series.dtype

    stats["null_count"] = series.null_count()
    stats["total_count"] = len(series)

    if dtype in (pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64, pl.Float32, pl.Float64):
        non_null = series.drop_nulls()
        if len(non_null) > 0:
            stats["mean"] = float(non_null.mean()) if non_null.mean() is not None else None
            stats["std"] = float(non_null.std()) if non_null.std() is not None else None
            stats["min"] = float(non_null.min()) if non_null.min() is not None else None
            stats["max"] = float(non_null.max()) if non_null.max() is not None else None
            stats["median"] = float(non_null.median()) if non_null.median() is not None else None
            try:
                q = non_null.quantile([0.25, 0.75])
                stats["q25"] = float(non_null.quantile(0.25))
                stats["q75"] = float(non_null.quantile(0.75))
            except Exception:
                pass

    elif dtype in (pl.Utf8, pl.String):
        non_null = series.drop_nulls().cast(pl.Utf8)
        if len(non_null) > 0:
            lengths = non_null.str.len_chars()
            stats["min_length"] = int(lengths.min()) if lengths.min() is not None else 0
            stats["max_length"] = int(lengths.max()) if lengths.max() is not None else 0
            stats["mean_length"] = float(lengths.mean()) if lengths.mean() is not None else 0.0

    return stats


def compute_pattern_distribution(series: pl.Series, max_patterns: int = 10) -> dict[str, float]:
    """Compute character-class pattern distribution using AutoCSV-LED shapes."""
    if series.dtype not in (pl.Utf8, pl.String):
        return {}

    non_null = series.drop_nulls().cast(pl.Utf8)
    if len(non_null) == 0:
        return {}

    shapes = [_shape(str(v)) for v in non_null.to_list()]
    from collections import Counter
    counter = Counter(shapes)
    total = len(shapes)

    # Keep top patterns
    top = counter.most_common(max_patterns)
    return {shape: round(count / total, 4) for shape, count in top}


def profile_column(series: pl.Series, column_name: str, column_index: int) -> ColumnProfile:
    """Profile a single column."""
    observed_type = infer_observed_type(series)
    semantic_type, semantic_confidence = infer_semantic_type(series, column_name)
    pii_likelihood = detect_pii_likelihood(series, column_name)
    statistics = compute_statistics(series)
    pattern_dist = compute_pattern_distribution(series)

    n_total = len(series)
    n_null = series.null_count()
    n_unique = series.n_unique()

    # Check for disguised nulls in string columns
    disguised_null_count = 0
    if series.dtype in (pl.Utf8, pl.String):
        non_null_strings = series.drop_nulls().cast(pl.Utf8)
        disguised_null_count = sum(
            1 for v in non_null_strings.to_list()
            if str(v).strip().lower() in NULL_TOKENS
        )

    effective_null_count = n_null + disguised_null_count
    missing_rate = effective_null_count / n_total if n_total > 0 else 0.0
    unique_rate = n_unique / n_total if n_total > 0 else 0.0

    # Sample values (non-null, up to 5)
    non_null = series.drop_nulls()
    sample_size = min(5, len(non_null))
    examples = non_null.sample(sample_size, seed=42).to_list() if sample_size > 0 else []

    # Date likelihood
    date_likelihood = 0.0
    if semantic_type and "date" in semantic_type:
        date_likelihood = semantic_confidence
    elif observed_type == "datetime":
        date_likelihood = 1.0

    return ColumnProfile(
        column_name=column_name,
        column_index=column_index,
        observed_type=observed_type,
        semantic_type=semantic_type,
        semantic_confidence=semantic_confidence,
        missing_rate=round(missing_rate, 4),
        unique_rate=round(unique_rate, 4),
        cardinality=n_unique,
        statistics=statistics,
        pattern_distribution=pattern_dist,
        examples=examples,
        pii_likelihood=round(pii_likelihood, 4),
        date_likelihood=round(date_likelihood, 4),
    )


def profile_dataframe(df: pl.DataFrame) -> list[ColumnProfile]:
    """Profile all columns in a DataFrame."""
    profiles = []
    for i, col_name in enumerate(df.columns):
        try:
            profile = profile_column(df[col_name], col_name, i)
            profiles.append(profile)
        except Exception as e:
            logger.warning(f"Failed to profile column '{col_name}': {e}")
            profiles.append(ColumnProfile(
                column_name=col_name,
                column_index=i,
                observed_type="unknown",
            ))
    return profiles
