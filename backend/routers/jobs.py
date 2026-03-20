from __future__ import annotations

from pathlib import Path
from typing import Optional
import logging

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict

from backend.services.job_service import enqueue_analysis, get_task_result, map_task_status, task_progress

router = APIRouter(tags=["jobs"])
logger = logging.getLogger(__name__)


class AnalyzeRequest(BaseModel):
    input_path: str


class AnalyzeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    job_id: str
    status: str
    input_path: Optional[str] = None
    umap_coordinates: Optional[list[list[float]]] = None
    cluster_labels: Optional[list[str]] = None


class StatusResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    job_id: str
    status: str
    progress: int
    error: Optional[str] = None


class ResultsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    job_id: str
    status: str
    output_path: Optional[str] = None
    n_obs: Optional[int] = None
    n_vars: Optional[int] = None
    umap_coordinates: Optional[list[list[float]]] = None
    cluster_labels: Optional[list[str]] = None


@router.post("/upload")
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
        logger.info("Uploaded file stored path=%s", out_path)
        payload = AnalyzeResponse(job_id="", status="uploaded", input_path=str(out_path)).model_dump()
        return {"status": "success", "data": payload, "error": None}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Upload failed file=%s error=%s", file.filename, exc)
        raise HTTPException(status_code=500, detail="Failed to store uploaded file.")


@router.post("/analyze")
def analyze(req: AnalyzeRequest):
    path = Path(req.input_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Input file not found.")
    if path.suffix.lower() not in {".h5ad", ".csv"}:
        raise HTTPException(status_code=400, detail="Only .h5ad or .csv input is supported.")
    try:
        job_id = enqueue_analysis(str(path))
        payload = AnalyzeResponse(
            job_id=job_id,
            status="queued",
            input_path=str(path),
            umap_coordinates=None,
            cluster_labels=None,
        ).model_dump()
        return {"status": "success", "data": payload, "error": None}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Analyze endpoint failed input=%s error=%s", req.input_path, exc)
        raise HTTPException(status_code=500, detail="Analysis failed.")


@router.get("/status/{job_id}")
def status(job_id: str):
    task = get_task_result(job_id)
    status_value = map_task_status(task)
    error_msg = str(task.result) if status_value == "failed" and task.result else None
    payload = StatusResponse(
        job_id=job_id,
        status=status_value,
        progress=task_progress(task),
        error=error_msg,
    ).model_dump()
    return {"status": "success", "data": payload, "error": None}


@router.get("/results/{job_id}")
def results(job_id: str):
    task = get_task_result(job_id)
    status_value = map_task_status(task)
    if status_value != "completed":
        raise HTTPException(status_code=409, detail=f"Job is not completed (status={status_value}).")
    task_data = task.result if isinstance(task.result, dict) else {}
    payload = ResultsResponse(
        job_id=job_id,
        status=status_value,
        output_path=task_data.get("output_path"),
        n_obs=task_data.get("n_obs"),
        n_vars=task_data.get("n_vars"),
        umap_coordinates=task_data.get("umap_coordinates"),
        cluster_labels=task_data.get("cluster_labels"),
    ).model_dump()
    return {"status": "success", "data": payload, "error": None}
