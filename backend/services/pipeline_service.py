from __future__ import annotations

import json
import logging
import hashlib
import os
import re
import subprocess
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
SLURM_RESULTS_DIR = Path(os.getenv("SLURM_RESULTS_DIR", "data/slurm_results"))


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
        if _analysis_runner() == "slurm":
            result_path = SLURM_RESULTS_DIR / f"{job_id}.json"
            try:
                slurm_job_id = _submit_slurm_job(str(path), result_path)
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Failed to submit SLURM job: {exc}") from exc
            JOBS[job_id] = {
                "status": "queued",
                "result": {},
                "error": None,
                "runner": "slurm",
                "slurm_job_id": slurm_job_id,
                "result_path": str(result_path),
                "file_hash": file_hash,
            }
            return job_id
        JOBS[job_id] = {"status": "running", "result": {}, "error": None, "runner": "local", "file_hash": file_hash}
    Thread(target=_execute_job, args=(job_id, str(path), file_hash), daemon=True).start()
    return job_id


def get_analysis_status(job_id: str) -> dict:
    with _JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.get("runner") == "slurm":
        _refresh_slurm_job(job_id, job)
        with _JOBS_LOCK:
            job = JOBS.get(job_id) or job
    status_value = str(job.get("status", "running"))
    error_msg = str(job.get("error")) if job.get("error") else None
    progress = 5 if status_value == "queued" else (60 if status_value == "running" else 100)
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
    if job.get("runner") == "slurm":
        _refresh_slurm_job(job_id, job)
        with _JOBS_LOCK:
            job = JOBS.get(job_id) or job
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


def _analysis_runner() -> str:
    mode = os.getenv("ANALYSIS_RUNNER", "local").strip().lower()
    return "slurm" if mode == "slurm" else "local"


def _submit_slurm_job(input_path: str, result_path: Path) -> str:
    script = Path("scripts/hpc/run_pipeline.sbatch")
    if not script.exists():
        raise RuntimeError(f"SLURM script not found: {script}")
    result_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["sbatch", str(script), input_path, str(result_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    out = (proc.stdout or "").strip()
    match = re.search(r"Submitted batch job\s+(\d+)", out)
    if not match:
        raise RuntimeError(f"Unexpected sbatch output: {out or proc.stderr}")
    return match.group(1)


def _refresh_slurm_job(job_id: str, job: dict) -> None:
    slurm_job_id = str(job.get("slurm_job_id", "")).strip()
    result_path = Path(str(job.get("result_path", "")))
    file_hash = str(job.get("file_hash", "")).strip()
    if result_path.exists():
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            result = payload.get("result") if isinstance(payload, dict) else None
            if payload.get("status") == "success" and isinstance(result, dict):
                with _JOBS_LOCK:
                    if file_hash:
                        CACHE[file_hash] = result
                    JOBS[job_id] = {**job, "status": "completed", "result": result, "error": None}
                return
            error = payload.get("error") if isinstance(payload, dict) else "SLURM job failed."
            with _JOBS_LOCK:
                JOBS[job_id] = {**job, "status": "failed", "result": {}, "error": str(error or "SLURM job failed.")}
            return
        except Exception as exc:
            with _JOBS_LOCK:
                JOBS[job_id] = {**job, "status": "failed", "result": {}, "error": f"Invalid SLURM result file: {exc}"}
            return
    if not slurm_job_id:
        with _JOBS_LOCK:
            JOBS[job_id] = {**job, "status": "failed", "result": {}, "error": "Missing SLURM job id."}
        return
    slurm_state = _get_slurm_state(slurm_job_id)
    mapped = _map_slurm_state(slurm_state)
    with _JOBS_LOCK:
        if mapped == "failed":
            JOBS[job_id] = {**job, "status": "failed", "result": {}, "error": f"SLURM state: {slurm_state}"}
        else:
            JOBS[job_id] = {**job, "status": mapped}


def _get_slurm_state(slurm_job_id: str) -> str:
    sacct_cmd = ["sacct", "-j", slurm_job_id, "--format=State", "--noheader"]
    try:
        out = subprocess.run(sacct_cmd, capture_output=True, text=True, check=True).stdout
        states = [line.strip().split()[0] for line in (out or "").splitlines() if line.strip()]
        if states:
            return states[0]
    except Exception:
        pass
    squeue_cmd = ["squeue", "-j", slurm_job_id, "-h", "-o", "%T"]
    try:
        out = subprocess.run(squeue_cmd, capture_output=True, text=True, check=True).stdout.strip()
        if out:
            return out.splitlines()[0].strip()
    except Exception:
        pass
    return "UNKNOWN"


def _map_slurm_state(state: str) -> str:
    s = (state or "").upper()
    if s in {"PENDING", "CONFIGURING"}:
        return "queued"
    if s in {"RUNNING", "COMPLETING"}:
        return "running"
    if s in {"COMPLETED"}:
        return "running"
    if s in {"FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY", "NODE_FAIL", "BOOT_FAIL", "PREEMPTED"}:
        return "failed"
    return "queued"
