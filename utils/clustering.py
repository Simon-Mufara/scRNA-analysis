import scanpy as sc
import numpy as np
from config import N_TOP_GENES, N_PCS, N_NEIGHBORS, LEIDEN_RESOLUTION


def run_clustering(adata, n_top_genes=N_TOP_GENES, n_pcs=N_PCS,
                   n_neighbors=N_NEIGHBORS, resolution=LEIDEN_RESOLUTION):
    """Full normalization → HVG → PCA → neighbors → UMAP → Leiden pipeline."""
    from scipy.sparse import issparse

    # ── 1. Normalize (skip if already done to avoid double-normalization) ──
    # Heuristic: if max count per cell >> 1e4, data is likely raw counts
    X = adata.X
    if issparse(X):
        cell_totals = np.array(X.sum(axis=1)).flatten()
    else:
        cell_totals = np.array(X).sum(axis=1)

    median_total = float(np.median(cell_totals))
    if median_total > 500:           # raw or unnormalized → normalize
        sc.pp.normalize_total(adata, target_sum=1e4)
        sc.pp.log1p(adata)
    # else: already log-normalized, skip

    # ── 2. Remove genes with all-zero mean (cause NaN bins in HVG) ──────────
    X2 = adata.X
    if issparse(X2):
        gene_means = np.array(X2.mean(axis=0)).flatten()
    else:
        gene_means = np.array(X2).mean(axis=0)

    nonzero_mask = gene_means > 0
    if not nonzero_mask.all():
        adata = adata[:, nonzero_mask].copy()

    # ── 3. Highly variable genes ──────────────────────────────────────────────
    # min_mean/max_mean protect against degenerate bins; n_bins=20 is robust
    sc.pp.highly_variable_genes(
        adata,
        n_top_genes=min(n_top_genes, adata.n_vars),
        min_mean=0.0125,
        max_mean=3,
        min_disp=0.5,
        n_bins=20,
    )
    adata.raw = adata  # preserve pre-scale counts for DE

    # ── 4. PCA → neighbors → UMAP → Leiden ──────────────────────────────────
    sc.pp.scale(adata, max_value=10)

    n_pcs_actual = min(n_pcs, adata.n_vars - 1, adata.n_obs - 1)
    sc.pp.pca(adata, n_comps=n_pcs_actual, use_highly_variable=True)

    n_neighbors_actual = min(n_neighbors, adata.n_obs - 1)
    sc.pp.neighbors(adata, n_neighbors=n_neighbors_actual, n_pcs=n_pcs_actual)

    sc.tl.umap(adata)
    sc.tl.leiden(adata, resolution=resolution)

    return adata
