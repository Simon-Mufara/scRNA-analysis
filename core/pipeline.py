import logging
from anndata import AnnData
import pandas as pd
import scanpy as sc
from pathlib import Path

from core.clustering import cluster, normalize, run_pca, run_umap
from core.preprocessing import convert_h5ad_to_zarr, load_h5ad_safe, load_input_dataset
from core.qc import compute_qc_metrics, qc_filter

logger = logging.getLogger(__name__)


def _write_checkpoint(adata: AnnData, *, artifact_id: str, step: str) -> None:
    out_dir = Path("data/processed")
    out_dir.mkdir(parents=True, exist_ok=True)
    adata.write_h5ad(out_dir / f"{artifact_id}_{step}.h5ad")


def run_pipeline(file_path: str, job_id: str | None = None) -> AnnData:
    artifact_id = str(job_id or Path(file_path).stem)
    suffix = Path(file_path).suffix.lower()
    if suffix == ".csv":
        adata = load_input_dataset(file_path, ".csv")
    elif suffix == ".loom":
        adata = load_input_dataset(file_path, ".loom")
    elif suffix == ".zarr":
        adata = load_input_dataset(file_path, ".zarr")
    else:
        if suffix == ".h5ad":
            try:
                zarr_path = convert_h5ad_to_zarr(file_path)
                adata = load_input_dataset(zarr_path, ".zarr")
            except Exception:
                adata = load_h5ad_safe(file_path)
        else:
            adata = load_h5ad_safe(file_path)
    if hasattr(adata, "isbacked") and getattr(adata, "isbacked", False):
        adata = adata.to_memory()
    logger.info("Loaded dataset: %s cells", adata.n_obs)
    _write_checkpoint(adata, artifact_id=artifact_id, step="loaded")
    if adata.n_obs > 100_000:
        logger.warning("Subsampling event: %s -> 50000 cells", adata.n_obs)
        sc.pp.subsample(adata, n_obs=50_000, random_state=0)
        logger.info("Subsampling complete: %s cells", adata.n_obs)
    logger.info("Running QC metrics...")
    adata = compute_qc_metrics(adata)
    logger.info("Completed QC metrics.")
    logger.info("Running QC filter...")
    adata = qc_filter(
        adata,
        min_genes=200,
        max_genes=5000,
        min_cells=3,
        max_mito=20.0,
        remove_doublets=False,
    )
    logger.info("Completed QC filter.")
    _write_checkpoint(adata, artifact_id=artifact_id, step="qc")
    logger.info("Running normalization...")
    adata = normalize(adata)
    logger.info("Completed normalization.")
    logger.info("Running PCA...")
    adata = run_pca(adata)
    logger.info("Completed PCA.")
    _write_checkpoint(adata, artifact_id=artifact_id, step="pca")
    logger.info("Running UMAP...")
    adata = run_umap(adata)
    logger.info("Completed UMAP.")
    _write_checkpoint(adata, artifact_id=artifact_id, step="umap")
    logger.info("Running clustering...")
    adata = cluster(adata)
    logger.info("Completed clustering.")
    _write_checkpoint(adata, artifact_id=artifact_id, step="clustered")
    return adata


def load_dataset_by_format(file_path: str, fmt: str):
    return load_input_dataset(file_path, fmt)


def run_differential_expression(adata, *, groupby_col: str, method: str, n_genes: int):
    sc.tl.rank_genes_groups(adata, groupby=groupby_col, method=method, n_genes=int(n_genes))
    return adata


def get_ranked_genes_df(adata, *, group: str) -> pd.DataFrame:
    return sc.get.rank_genes_groups_df(adata, group=str(group))


def build_prerank_input(adata, *, group: str) -> pd.DataFrame:
    de_df = get_ranked_genes_df(adata, group=group)
    return pd.DataFrame({"gene": de_df["names"].astype(str), "score": de_df["scores"].astype(float)})


def generate_marker_dotplot(adata, genes: list[str], groupby: str, color_map: str = "viridis"):
    return sc.pl.dotplot(adata, genes, groupby=groupby, show=False, return_fig=True, color_map=color_map)
