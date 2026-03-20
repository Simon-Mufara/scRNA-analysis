from __future__ import annotations

from celery.result import AsyncResult

from backend.services.celery_app import celery_app


def enqueue_analysis(input_path: str) -> str:
    from backend.services.tasks import analyze_pipeline_task

    task = analyze_pipeline_task.delay(input_path)
    return task.id


def get_task_result(job_id: str) -> AsyncResult:
    return AsyncResult(job_id, app=celery_app)


def map_task_status(task: AsyncResult) -> str:
    state = (task.state or "").upper()
    if state in {"PENDING", "RECEIVED"}:
        return "queued"
    if state in {"STARTED", "RETRY"}:
        return "running"
    if state == "SUCCESS":
        return "completed"
    if state in {"FAILURE", "REVOKED"}:
        return "failed"
    return "queued"


def task_progress(task: AsyncResult) -> int:
    status = map_task_status(task)
    if status == "queued":
        return 5
    if status == "running":
        return 60
    if status == "completed":
        return 100
    if status == "failed":
        return 100
    return 0

