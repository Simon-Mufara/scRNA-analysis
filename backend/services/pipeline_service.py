from __future__ import annotations

import logging
import hashlib
import time
from pathlib import Path
from threading import Lock, Thread
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from core.pipeline import run_pipeline

logger = logging.getLogger(__name__)

ALLOWED_SUFFIXES = {".h5ad", ".csv"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024 * 1024
JOBS: dict[str, dict] = {}
CACHE: dict[str, dict] = {}
_JOBS_LOCK = Lock()


async def save_upload(file: UploadFile) -> str:
    logger.debug("upload started filename=%s", file.filename)
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="Only .h5ad or .csv files are supported.")
    out_dir = Path("data/uploads")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / str(file.filename)
    total_bytes = 0
    chunk_size = 8 * 1024 * 1024
    with out_path.open("wb") as buffer:
        while True:
            chunk = file.file.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_UPLOAD_BYTES:
                buffer.close()
                out_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File too large. Max supported size is 20GB.")
            buffer.write(chunk)
    if out_path.stat().st_size == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    logger.debug("upload completed filename=%s size_bytes=%s", file.filename, out_path.stat().st_size)
    return str(out_path)


def start_analysis(input_path: str) -> str:
    path = Path(input_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Input file not found.")
    if path.suffix.lower() not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="Only .h5ad or .csv input is supported.")
    job_id = str(uuid4())
    file_hash = _hash_file(path)
    with _JOBS_LOCK:
        cached = CACHE.get(file_hash)
        if cached is not None:
            JOBS[job_id] = {"status": "completed", "result": cached, "error": None}
            return job_id
        JOBS[job_id] = {"status": "running", "result": {}, "error": None}
    Thread(target=_execute_job, args=(job_id, str(path), file_hash), daemon=True).start()
    return job_id


def get_analysis_status(job_id: str) -> dict:
    with _JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    status_value = str(job.get("status", "running"))
    error_msg = str(job.get("error")) if job.get("error") else None
    progress = 60 if status_value == "running" else 100
    return {
        "job_id": job_id,
        "status": status_value,
        "progress": progress,
        "error": error_msg,
    }


def get_analysis_results(job_id: str) -> dict:
    with _JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    status_value = str(job.get("status", "running"))
    if status_value != "completed":
        raise HTTPException(status_code=409, detail=f"Job is not completed (status={status_value}).")
    task_data = job.get("result") if isinstance(job.get("result"), dict) else {}
    return {
        "job_id": job_id,
        "status": status_value,
        "output_path": task_data.get("output_path"),
        "n_obs": task_data.get("n_obs"),
        "n_vars": task_data.get("n_vars"),
        "umap": task_data.get("umap", task_data.get("umap_coordinates")),
        "clusters": task_data.get("clusters", task_data.get("cluster_labels")),
        "umap_coordinates": task_data.get("umap_coordinates", task_data.get("umap")),
        "cluster_labels": task_data.get("cluster_labels", task_data.get("clusters")),
    }


def _execute_job(job_id: str, input_path: str, file_hash: str) -> None:
    try:
        result = run_pipeline_for_file(input_path, job_id=job_id)
        with _JOBS_LOCK:
            CACHE[file_hash] = result
            JOBS[job_id] = {"status": "completed", "result": result, "error": None}
    except Exception as exc:
        logger.exception("Failed at step pipeline for file %s: %s", input_path, exc)
        with _JOBS_LOCK:
            JOBS[job_id] = {"status": "failed", "result": {}, "error": str(exc)}


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_pipeline_for_file(input_path: str, job_id: str | None = None) -> dict:
    started_at = time.perf_counter()
    logger.info("Running pipeline for file %s", input_path)
    try:
        file_size_bytes = Path(input_path).stat().st_size
    except OSError:
        file_size_bytes = 0
    logger.info("Input file size: %.2f GB", file_size_bytes / (1024 ** 3))
    adata = run_pipeline(input_path, job_id=job_id)
    out_path = str(Path(input_path).with_name(f"{Path(input_path).stem}_analyzed.h5ad"))
    adata.write_h5ad(out_path)
    if "X_umap" not in adata.obsm:
        raise ValueError("UMAP coordinates were not generated.")
    if "leiden" not in adata.obs.columns:
        raise ValueError("Cluster labels (leiden) were not generated.")
    umap = adata.obsm["X_umap"].tolist()
    clusters = adata.obs["leiden"].astype(str).tolist()
    result = {
        "output_path": out_path,
        "n_obs": int(adata.n_obs),
        "n_vars": int(adata.n_vars),
        "umap": umap,
        "clusters": clusters,
        "umap_coordinates": umap,
        "cluster_labels": clusters,
    }
    logger.info("Completed pipeline for file %s", input_path)
    logger.debug("pipeline completed in %.2f seconds", time.perf_counter() - started_at)
    return result
