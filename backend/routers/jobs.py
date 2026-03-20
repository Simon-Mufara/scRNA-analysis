from __future__ import annotations

from typing import Optional
import logging

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict

from backend.services.pipeline_service import (
    get_analysis_results,
    get_analysis_status,
    save_upload,
    start_analysis,
)

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
    umap: Optional[list[list[float]]] = None
    clusters: Optional[list[str]] = None
    umap_coordinates: Optional[list[list[float]]] = None
    cluster_labels: Optional[list[str]] = None


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    logger.debug("endpoint=/upload started")
    logger.info("Starting file upload for %s", file.filename)
    try:
        out_path = await save_upload(file)
        logger.info("Completed file upload for %s", file.filename)
        payload = AnalyzeResponse(job_id="", status="uploaded", input_path=str(out_path)).model_dump()
        return {"status": "success", "data": payload, "error": None}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed at step upload for file %s: %s", file.filename, exc)
        raise HTTPException(status_code=500, detail="Failed to store uploaded file.")


@router.post("/analyze")
def analyze(req: AnalyzeRequest):
    logger.debug("endpoint=/analyze started")
    try:
        job_id = start_analysis(req.input_path)
        payload = AnalyzeResponse(
            job_id=job_id,
            status="running",
            input_path=req.input_path,
            umap_coordinates=None,
            cluster_labels=None,
        ).model_dump()
        return {"status": "success", "data": payload, "error": None}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed at step analyze for file %s: %s", req.input_path, exc)
        raise HTTPException(status_code=500, detail="Analysis failed.")


@router.get("/status/{job_id}")
def status(job_id: str):
    logger.debug("endpoint=/status started")
    payload = StatusResponse(**get_analysis_status(job_id)).model_dump()
    return {"status": "success", "data": payload, "error": None}


@router.get("/results/{job_id}")
def results(job_id: str):
    logger.debug("endpoint=/results started")
    payload = ResultsResponse(**get_analysis_results(job_id)).model_dump()
    return {"status": "success", "data": payload, "error": None}
