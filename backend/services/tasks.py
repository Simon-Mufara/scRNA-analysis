from __future__ import annotations

import logging
from pathlib import Path

from backend.services.celery_app import celery_app
from core.pipeline import run_pipeline

logger = logging.getLogger(__name__)


@celery_app.task(name="backend.analyze_pipeline")
def analyze_pipeline_task(input_path: str) -> dict:
    logger.info("Celery task started input=%s", input_path)
    adata = run_pipeline(input_path)
    out_path = str(Path(input_path).with_name(f"{Path(input_path).stem}_analyzed.h5ad"))
    adata.write_h5ad(out_path)
    if "X_umap" not in adata.obsm:
        raise ValueError("UMAP coordinates were not generated.")
    if "leiden" not in adata.obs.columns:
        raise ValueError("Cluster labels (leiden) were not generated.")
    result = {
        "output_path": out_path,
        "n_obs": int(adata.n_obs),
        "n_vars": int(adata.n_vars),
        "umap_coordinates": adata.obsm["X_umap"].tolist(),
        "cluster_labels": adata.obs["leiden"].astype(str).tolist(),
    }
    logger.info("Celery task completed input=%s output=%s", input_path, out_path)
    return result

