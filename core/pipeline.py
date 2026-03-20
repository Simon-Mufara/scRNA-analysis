from anndata import AnnData
import pandas as pd
import scanpy as sc
from pathlib import Path

from core.clustering import run_clustering_step
from core.preprocessing import load_h5ad_safe, load_input_dataset
from core.qc import compute_qc_metrics, run_qc_filter


def run_pipeline(file_path: str) -> AnnData:
    suffix = Path(file_path).suffix.lower()
    if suffix == ".csv":
        adata = load_input_dataset(file_path, ".csv")
    elif suffix == ".loom":
        adata = load_input_dataset(file_path, ".loom")
    else:
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
