from __future__ import annotations

from backend.services.celery_app import celery_app
from backend.services.pipeline_service import run_pipeline_for_file


@celery_app.task(name="backend.analyze_pipeline")
def analyze_pipeline_task(input_path: str) -> dict:
    return run_pipeline_for_file(input_path)
