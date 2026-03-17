import scanpy as sc
import numpy as np
from config import QC_MIN_GENES, QC_MAX_GENES, QC_MIN_CELLS, QC_MAX_MITO_PCT


def run_qc(adata, min_genes=QC_MIN_GENES, max_genes=QC_MAX_GENES,
           min_cells=QC_MIN_CELLS, max_mito=QC_MAX_MITO_PCT):
    """Run standard QC filtering on AnnData object."""

    # Flag mitochondrial genes
    adata.var["mt"] = adata.var_names.str.upper().str.startswith("MT-")

    sc.pp.calculate_qc_metrics(
        adata, qc_vars=["mt"], percent_top=None, log1p=False, inplace=True
    )

    before = adata.n_obs

    # Filter cells by gene count
    sc.pp.filter_cells(adata, min_genes=min_genes)
    sc.pp.filter_cells(adata, max_genes=max_genes)

    # Filter genes by cell count
    sc.pp.filter_genes(adata, min_cells=min_cells)

    # Filter by mitochondrial content
    adata = adata[adata.obs["pct_counts_mt"] < max_mito].copy()

    after = adata.n_obs
    adata.uns["qc_summary"] = {
        "cells_before": before,
        "cells_after": after,
        "cells_removed": before - after,
    }

    return adata


def get_qc_stats(adata):
    """Return a summary dict of QC metrics."""
    stats = {
        "n_cells": adata.n_obs,
        "n_genes": adata.n_vars,
        "median_genes_per_cell": float(np.median(adata.obs["n_genes_by_counts"])),
        "median_counts_per_cell": float(np.median(adata.obs["total_counts"])),
    }
    if "pct_counts_mt" in adata.obs.columns:
        stats["median_mito_pct"] = float(np.median(adata.obs["pct_counts_mt"]))
    return stats
