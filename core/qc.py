import scanpy as sc

from utils.preprocessing import get_qc_stats as _get_qc_stats
from utils.preprocessing import run_qc as _run_qc


def compute_qc_metrics(adata):
    if "pct_counts_mt" not in adata.obs.columns:
        adata.var["mt"] = adata.var_names.str.upper().str.startswith("MT-")
        sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], percent_top=None, log1p=False, inplace=True)
    return adata


def run_qc_filter(adata, *, min_genes: int, max_genes: int, min_cells: int, max_mito: float, remove_doublets: bool = False):
    return _run_qc(
        adata,
        min_genes=min_genes,
        max_genes=max_genes,
        min_cells=min_cells,
        max_mito=max_mito,
        remove_doublets=remove_doublets,
    )


def get_qc_stats(adata):
    return _get_qc_stats(adata)

