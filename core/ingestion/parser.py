"""Unified tabular data parser — CSV, XLSX, Parquet.

Uses Polars for maximum performance. Falls back gracefully
on edge cases (encoding, malformed rows, etc.).

INVARIANT: Original data is IMMUTABLE — parser stores a copy.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

import chardet
import polars as pl

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".pq"}
MAX_SAMPLE_ROWS = 100  # For encoding detection


def detect_encoding(file_path: Path) -> str:
    """Detect file encoding using chardet on the first chunk."""
    with open(file_path, "rb") as f:
        raw = f.read(min(file_path.stat().st_size, 1024 * 100))  # First 100KB
    result = chardet.detect(raw)
    encoding = result.get("encoding", "utf-8") or "utf-8"
    confidence = result.get("confidence", 0.0)
    logger.info(f"Detected encoding: {encoding} (confidence={confidence:.2f})")
    return encoding


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def parse_csv(file_path: Path, encoding: str = "utf-8") -> tuple[pl.DataFrame, list[str]]:
    """Parse CSV/TSV file to Polars DataFrame.

    Returns:
        Tuple of (DataFrame, list of warnings).
    """
    warnings: list[str] = []
    separator = "\t" if file_path.suffix == ".tsv" else ","

    try:
        df = pl.read_csv(
            file_path,
            separator=separator,
            encoding=encoding,
            infer_schema_length=10000,
            try_parse_dates=False,  # Keep dates as strings for format detection
            ignore_errors=True,
            truncate_ragged_lines=True,
        )
    except Exception as e:
        # Fallback: try with different settings
        logger.warning(f"Primary CSV parse failed: {e}, trying fallback")
        warnings.append(f"Primary parse failed: {str(e)[:200]}")
        try:
            df = pl.read_csv(
                file_path,
                separator=separator,
                encoding="utf-8",
                has_header=True,
                ignore_errors=True,
                truncate_ragged_lines=True,
            )
        except Exception as e2:
            raise ValueError(f"Cannot parse CSV file: {e2}") from e2

    # Check for common issues
    if df.is_empty():
        warnings.append("Dataset is empty (0 rows)")

    if len(df.columns) < 2:
        warnings.append("Dataset has fewer than 2 columns — possible delimiter issue")

    # Check for duplicate column names
    if len(set(df.columns)) < len(df.columns):
        warnings.append("Duplicate column names detected")
        # Rename duplicates
        seen: dict[str, int] = {}
        new_cols = []
        for col in df.columns:
            if col in seen:
                seen[col] += 1
                new_cols.append(f"{col}_{seen[col]}")
            else:
                seen[col] = 0
                new_cols.append(col)
        df.columns = new_cols

    return df, warnings


def parse_xlsx(file_path: Path) -> tuple[pl.DataFrame, list[str]]:
    """Parse Excel file to Polars DataFrame."""
    warnings: list[str] = []
    try:
        df = pl.read_excel(file_path, engine="openpyxl")
    except Exception as e:
        raise ValueError(f"Cannot parse Excel file: {e}") from e

    if df.is_empty():
        warnings.append("Dataset is empty (0 rows)")

    return df, warnings


def parse_parquet(file_path: Path) -> tuple[pl.DataFrame, list[str]]:
    """Parse Parquet file to Polars DataFrame."""
    warnings: list[str] = []
    try:
        df = pl.read_parquet(file_path)
    except Exception as e:
        raise ValueError(f"Cannot parse Parquet file: {e}") from e

    return df, warnings


def parse_file(file_path: Path) -> tuple[pl.DataFrame, dict[str, Any]]:
    """Parse any supported file format.

    Returns:
        Tuple of (DataFrame, metadata dict).
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported file format: {suffix}. "
            f"Supported: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )

    file_size = path.stat().st_size
    sha256 = compute_sha256(path)

    metadata: dict[str, Any] = {
        "original_filename": path.name,
        "file_format": suffix.lstrip("."),
        "file_size_bytes": file_size,
        "sha256": sha256,
    }

    if suffix in (".csv", ".tsv"):
        encoding = detect_encoding(path)
        metadata["encoding"] = encoding
        df, warnings = parse_csv(path, encoding)
    elif suffix in (".xlsx", ".xls"):
        metadata["encoding"] = "n/a"
        df, warnings = parse_xlsx(path)
    elif suffix in (".parquet", ".pq"):
        metadata["encoding"] = "n/a"
        df, warnings = parse_parquet(path)
    else:
        raise ValueError(f"Unsupported format: {suffix}")

    metadata["row_count"] = len(df)
    metadata["column_count"] = len(df.columns)
    metadata["columns"] = list(df.columns)
    metadata["parser_warnings"] = warnings

    logger.info(
        f"Parsed {path.name}: {len(df)} rows × {len(df.columns)} cols, "
        f"format={metadata['file_format']}"
    )

    return df, metadata
