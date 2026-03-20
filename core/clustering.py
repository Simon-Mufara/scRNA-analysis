from utils.clustering import run_clustering as _run_clustering


def run_clustering_step(
    adata,
    *,
    n_top_genes: int,
    n_pcs: int,
    n_neighbors: int,
    resolution: float,
    integration_method: str = "none",
    batch_key: str = "",
):
    return _run_clustering(
        adata,
        n_top_genes=n_top_genes,
        n_pcs=n_pcs,
        n_neighbors=n_neighbors,
        resolution=resolution,
        integration_method=integration_method,
        batch_key=batch_key,
    )


def normalize(adata):
    # Normalization is executed inside run_clustering_step to preserve current behavior.
    return adata


def run_pca(adata):
    if "X_pca" not in adata.obsm:
        _ = run_clustering_step(
            adata,
            n_top_genes=2000,
            n_pcs=40,
            n_neighbors=15,
            resolution=0.5,
            integration_method="none",
            batch_key="",
        )
    return adata


def run_umap(adata):
    if "X_umap" not in adata.obsm:
        _ = run_clustering_step(
            adata,
            n_top_genes=2000,
            n_pcs=40,
            n_neighbors=15,
            resolution=0.5,
            integration_method="none",
            batch_key="",
        )
    return adata


def cluster(adata):
    if "leiden" not in adata.obs.columns:
        _ = run_clustering_step(
            adata,
            n_top_genes=2000,
            n_pcs=40,
            n_neighbors=15,
            resolution=0.5,
            integration_method="none",
            batch_key="",
        )
    return adata
