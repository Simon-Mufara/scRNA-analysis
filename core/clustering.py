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

