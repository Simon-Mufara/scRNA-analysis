import scanpy as sc
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt


def umap_plot(adata, color="leiden", title="UMAP"):
    """Return an interactive Plotly UMAP scatter plot."""
    df = pd.DataFrame({
        "UMAP1": adata.obsm["X_umap"][:, 0],
        "UMAP2": adata.obsm["X_umap"][:, 1],
        "color": adata.obs[color].astype(str),
    })
    fig = px.scatter(
        df, x="UMAP1", y="UMAP2", color="color",
        title=title, labels={"color": color},
        opacity=0.7, height=600,
    )
    fig.update_traces(marker=dict(size=3))
    fig.update_layout(legend=dict(itemsizing="constant"))
    return fig


def violin_qc(adata, keys=None):
    """Return a Plotly violin plot for QC metrics."""
    keys = keys or ["n_genes_by_counts", "total_counts", "pct_counts_mt"]
    available = [k for k in keys if k in adata.obs.columns]
    if not available:
        return None
    fig = go.Figure()
    for key in available:
        fig.add_trace(go.Violin(y=adata.obs[key], name=key, box_visible=True, meanline_visible=True))
    fig.update_layout(title="QC Metrics Distribution", height=400)
    return fig


def gene_umap_plot(adata, gene: str):
    """Color UMAP by a single gene's expression."""
    if gene not in adata.var_names:
        return None
    expr = np.array(adata[:, gene].X.todense()).flatten() if hasattr(adata[:, gene].X, "todense") \
        else np.array(adata[:, gene].X).flatten()
    df = pd.DataFrame({
        "UMAP1": adata.obsm["X_umap"][:, 0],
        "UMAP2": adata.obsm["X_umap"][:, 1],
        "expression": expr,
    })
    fig = px.scatter(
        df, x="UMAP1", y="UMAP2", color="expression",
        color_continuous_scale="Viridis",
        title=f"{gene} Expression", opacity=0.7, height=600,
    )
    fig.update_traces(marker=dict(size=3))
    return fig


def dotplot_markers(adata, marker_genes: list, groupby="leiden"):
    """Matplotlib dotplot for marker genes across clusters."""
    genes_present = [g for g in marker_genes if g in adata.var_names]
    if not genes_present:
        return None
    fig = sc.pl.dotplot(adata, genes_present, groupby=groupby, show=False, return_fig=True)
    return fig
