from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Dict, Literal, Optional
from uuid import uuid4

import scanpy as sc

from core.pipeline import run_pipeline

JobState = Literal["queued", "running", "completed", "failed"]


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
    try:
        adata = run_pipeline(job.input_path)
        out_path = str(Path(job.input_path).with_name(f"{Path(job.input_path).stem}_analyzed.h5ad"))
        adata.write_h5ad(out_path)
        job.status = "completed"
        job.output_path = out_path
        job.n_obs = int(adata.n_obs)
        job.n_vars = int(adata.n_vars)
        job.error = None
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
    finally:
        JOB_STORE.update(job)
    return job

