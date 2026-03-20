from __future__ import annotations

from pathlib import Path
from typing import Optional
import logging

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.services.job_service import JOB_STORE, analyze_job

router = APIRouter(tags=["jobs"])
logger = logging.getLogger(__name__)


class AnalyzeRequest(BaseModel):
    input_path: str


class AnalyzeResponse(BaseModel):
    job_id: str
    status: str
    umap_coordinates: Optional[list[list[float]]] = None
    cluster_labels: Optional[list[str]] = None


class StatusResponse(BaseModel):
    job_id: str
    status: str
    created_at: str
    updated_at: str
    output_path: Optional[str] = None
    error: Optional[str] = None


class ResultsResponse(BaseModel):
    job_id: str
    status: str
    output_path: Optional[str] = None
    n_obs: Optional[int] = None
    n_vars: Optional[int] = None
    umap_coordinates: Optional[list[list[float]]] = None
    cluster_labels: Optional[list[str]] = None


@router.post("/upload", response_model=AnalyzeResponse)
async def upload(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".h5ad", ".csv"}:
        raise HTTPException(status_code=400, detail="Only .h5ad or .csv files are supported.")
    out_dir = Path("data/uploads")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / file.filename
    try:
        payload = await file.read()
        if not payload:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        out_path.write_bytes(payload)
        job = JOB_STORE.create(str(out_path))
        logger.info("Uploaded file stored path=%s job=%s", out_path, job.job_id)
        return AnalyzeResponse(job_id=job.job_id, status=job.status)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Upload failed file=%s error=%s", file.filename, exc)
        raise HTTPException(status_code=500, detail="Failed to store uploaded file.")


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    path = Path(req.input_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Input file not found.")
    if path.suffix.lower() not in {".h5ad", ".csv"}:
        raise HTTPException(status_code=400, detail="Only .h5ad or .csv input is supported.")
    job = JOB_STORE.create(str(path))
    try:
        analyze_job(job.job_id)
        current = JOB_STORE.get(job.job_id)
        if not current:
            raise HTTPException(status_code=500, detail="Job disappeared unexpectedly.")
        return AnalyzeResponse(
            job_id=current.job_id,
            status=current.status,
            umap_coordinates=current.umap_coordinates,
            cluster_labels=current.cluster_labels,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Analyze endpoint failed input=%s error=%s", req.input_path, exc)
        raise HTTPException(status_code=500, detail="Analysis failed.")


@router.get("/status/{job_id}", response_model=StatusResponse)
def status(job_id: str):
    job = JOB_STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return StatusResponse(
        job_id=job.job_id,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        output_path=job.output_path,
        error=job.error,
    )


@router.get("/results/{job_id}", response_model=ResultsResponse)
def results(job_id: str):
    job = JOB_STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status != "completed":
        raise HTTPException(status_code=409, detail=f"Job is not completed (status={job.status}).")
    return ResultsResponse(
        job_id=job.job_id,
        status=job.status,
        output_path=job.output_path,
        n_obs=job.n_obs,
        n_vars=job.n_vars,
        umap_coordinates=job.umap_coordinates,
        cluster_labels=job.cluster_labels,
    )
