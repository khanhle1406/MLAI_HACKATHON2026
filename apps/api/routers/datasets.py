"""Dataset API routes — upload, list, get, delete."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from apps.api.config import settings
from core.audit.ledger import audit_ledger
from core.orchestrator.pipeline import pipeline

router = APIRouter(prefix="/datasets", tags=["datasets"])

# In-memory storage (will be replaced with DB)
_datasets: dict[str, dict[str, Any]] = {}
_analysis_results: dict[str, dict[str, Any]] = {}


@router.post("", status_code=201)
async def upload_dataset(file: UploadFile = File(...)):
    """Upload a new dataset and run analysis pipeline.

    Accepts CSV, XLSX, TSV, or Parquet files.
    Returns dataset metadata and analysis results.
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".pq"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {suffix}. Supported: csv, tsv, xlsx, parquet",
        )

    # Check file size
    content = await file.read()
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max: {settings.max_file_size_mb}MB",
        )

    # Save file
    dataset_id = str(uuid.uuid4())
    upload_dir = settings.upload_path / dataset_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename

    with open(file_path, "wb") as f:
        f.write(content)

    # Run analysis pipeline
    try:
        result = await pipeline.analyze_file(file_path, dataset_id=dataset_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    # Store results
    _datasets[dataset_id] = {
        "id": dataset_id,
        "filename": file.filename,
        "file_format": suffix.lstrip("."),
        "file_size": len(content),
        "status": result.get("status", "UNKNOWN"),
        "profile": result.get("profile"),
        "summary": result.get("summary"),
    }
    _analysis_results[dataset_id] = result

    return {
        "dataset_id": dataset_id,
        "filename": file.filename,
        "status": result.get("status"),
        "summary": result.get("summary"),
        "profile": result.get("profile"),
    }


@router.get("")
async def list_datasets():
    """List all uploaded datasets."""
    return {
        "datasets": list(_datasets.values()),
        "total": len(_datasets),
    }


@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str):
    """Get dataset details including profile and analysis results."""
    if dataset_id not in _datasets:
        raise HTTPException(status_code=404, detail="Dataset not found")

    dataset = _datasets[dataset_id]
    analysis = _analysis_results.get(dataset_id, {})

    return {
        **dataset,
        "evidence": analysis.get("evidence", []),
        "decisions": analysis.get("decisions", []),
    }


@router.get("/{dataset_id}/decisions")
async def get_decisions(dataset_id: str):
    """Get all decisions for a dataset."""
    if dataset_id not in _analysis_results:
        raise HTTPException(status_code=404, detail="Dataset not found")

    analysis = _analysis_results[dataset_id]
    return {
        "dataset_id": dataset_id,
        "decisions": analysis.get("decisions", []),
        "summary": analysis.get("summary", {}),
    }


@router.delete("/{dataset_id}")
async def delete_dataset(dataset_id: str):
    """Delete a dataset and its analysis results."""
    if dataset_id not in _datasets:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Clean up files
    upload_dir = settings.upload_path / dataset_id
    if upload_dir.exists():
        shutil.rmtree(upload_dir)

    # Remove from memory
    _datasets.pop(dataset_id, None)
    _analysis_results.pop(dataset_id, None)

    audit_ledger.record("DELETE", "user", dataset_id)

    return {"status": "deleted", "dataset_id": dataset_id}
