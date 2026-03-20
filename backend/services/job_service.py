from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Dict, Literal, Optional
from uuid import uuid4

import logging

from core.pipeline import run_pipeline

JobState = Literal["queued", "running", "completed", "failed"]
logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class JobRecord:
    job_id: str
    input_path: str
    status: JobState = "queued"
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    output_path: Optional[str] = None
    error: Optional[str] = None
    n_obs: Optional[int] = None
    n_vars: Optional[int] = None
    umap_coordinates: Optional[list[list[float]]] = None
    cluster_labels: Optional[list[str]] = None


class InMemoryJobStore:
    def __init__(self) -> None:
        self._jobs: Dict[str, JobRecord] = {}
        self._lock = Lock()

    def create(self, input_path: str) -> JobRecord:
        with self._lock:
            job = JobRecord(job_id=str(uuid4()), input_path=input_path)
            self._jobs[job.job_id] = job
            return job

    def get(self, job_id: str) -> Optional[JobRecord]:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job: JobRecord) -> None:
        with self._lock:
            job.updated_at = _now_iso()
            self._jobs[job.job_id] = job


JOB_STORE = InMemoryJobStore()


def analyze_job(job_id: str) -> JobRecord:
    job = JOB_STORE.get(job_id)
    if not job:
        raise ValueError("Job not found.")
    if job.status in {"running", "completed"}:
        return job

    job.status = "running"
    JOB_STORE.update(job)
    logger.info("Starting analysis job=%s input=%s", job.job_id, job.input_path)
    try:
        adata = run_pipeline(job.input_path)
        out_path = str(Path(job.input_path).with_name(f"{Path(job.input_path).stem}_analyzed.h5ad"))
        adata.write_h5ad(out_path)
        if "X_umap" not in adata.obsm:
            raise ValueError("UMAP coordinates were not generated.")
        if "leiden" not in adata.obs.columns:
            raise ValueError("Cluster labels (leiden) were not generated.")
        job.status = "completed"
        job.output_path = out_path
        job.n_obs = int(adata.n_obs)
        job.n_vars = int(adata.n_vars)
        job.umap_coordinates = adata.obsm["X_umap"].tolist()
        job.cluster_labels = adata.obs["leiden"].astype(str).tolist()
        job.error = None
        logger.info("Completed analysis job=%s output=%s", job.job_id, out_path)
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        logger.exception("Analysis job failed job=%s error=%s", job.job_id, exc)
    finally:
        JOB_STORE.update(job)
    return job
