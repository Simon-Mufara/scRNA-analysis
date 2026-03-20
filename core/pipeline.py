from anndata import AnnData

from core.clustering import run_clustering_step
from core.preprocessing import load_h5ad_safe
from core.qc import compute_qc_metrics, run_qc_filter


def run_pipeline(file_path: str) -> AnnData:
    adata = load_h5ad_safe(file_path)
    adata = compute_qc_metrics(adata)
    adata = run_qc_filter(
        adata,
        min_genes=200,
        max_genes=5000,
        min_cells=3,
        max_mito=20.0,
        remove_doublets=False,
    )
    adata = run_clustering_step(
        adata,
        n_top_genes=2000,
        n_pcs=40,
        n_neighbors=15,
        resolution=0.5,
        integration_method="none",
        batch_key="",
    )
    return adata

