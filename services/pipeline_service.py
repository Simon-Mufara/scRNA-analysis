from dataclasses import dataclass

import scanpy as sc

from utils.annotation import annotate_cells, score_marker_genes
from utils.clustering import run_clustering
from utils.pathway import get_top_pathways
from utils.preprocessing import run_qc


@dataclass
class DatasetStats:
    n_obs: int
    n_vars: int


def load_adata(path: str):
    if path.lower().endswith(".loom"):
        return sc.read_loom(path)
    return sc.read_h5ad(path)


def save_adata(adata, path: str):
    if path.lower().endswith(".loom"):
        adata.write_loom(path)
    else:
        adata.write_h5ad(path)


def qc_dataset(adata, *, min_genes: int, max_genes: int, min_cells: int, max_mito: float, remove_doublets: bool = False):
    return run_qc(
        adata,
        min_genes=min_genes,
        max_genes=max_genes,
        min_cells=min_cells,
        max_mito=max_mito,
        remove_doublets=remove_doublets,
    )


def cluster_dataset(
    adata,
    *,
    n_top_genes: int,
    n_pcs: int,
    n_neighbors: int,
    resolution: float,
    integration_method: str = "none",
    batch_key: str = "",
):
    return run_clustering(
        adata,
        n_top_genes=n_top_genes,
        n_pcs=n_pcs,
        n_neighbors=n_neighbors,
        resolution=resolution,
        integration_method=integration_method,
        batch_key=batch_key,
    )


def annotate_marker_dataset(adata, *, score_threshold: float):
    return score_marker_genes(adata, score_threshold=score_threshold)


def annotate_celltypist_dataset(adata, *, model_name: str, majority_voting: bool = True):
    return annotate_cells(adata, model_name=model_name, majority_voting=majority_voting)


def pathway_from_genes(genes: list[str], *, top_n: int, gene_sets: str):
    return get_top_pathways(genes, top_n=top_n, gene_sets=gene_sets)

