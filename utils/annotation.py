import scanpy as sc
import pandas as pd
import numpy as np
import celltypist
from config import CELLTYPIST_MODEL

# ── Canonical marker gene dictionary ────────────────────────────────────────
# Based on PanglaoDB, CellMarker, and literature-curated references
CANONICAL_MARKERS = {
    "CD4 T cells":        ["CD3D", "CD3E", "CD4", "IL7R", "CCR7", "TCF7", "SELL"],
    "CD8 T cells":        ["CD3D", "CD3E", "CD8A", "CD8B", "GZMB", "PRF1", "IFNG"],
    "Regulatory T cells": ["CD3D", "CD4", "FOXP3", "IL2RA", "CTLA4", "TIGIT", "IKZF2"],
    "Exhausted T cells":  ["PDCD1", "LAG3", "HAVCR2", "TIGIT", "TOX", "ENTPD1"],
    "NK cells":           ["GNLY", "NKG7", "KLRD1", "NCAM1", "KLRB1", "FGFBP2"],
    "B cells":            ["CD19", "MS4A1", "CD79A", "CD79B", "IGHM", "BANK1"],
    "Plasma cells":       ["MZB1", "SDC1", "CD38", "IGKC", "IGHG1", "XBP1"],
    "CD14 Monocytes":     ["CD14", "LYZ", "CST3", "S100A8", "S100A9", "VCAN"],
    "CD16 Monocytes":     ["FCGR3A", "MS4A7", "VMO1", "FCER1G", "LST1"],
    "Dendritic cells":    ["FCER1A", "CST3", "CLEC9A", "LILRA4", "IRF8", "HLA-DQA1"],
    "pDC":                ["LILRA4", "IL3RA", "GZMB", "JCHAIN", "DERL3"],
    "Mast cells":         ["TPSAB1", "TPSB2", "CPA3", "HPGDS", "KIT"],
    "Platelets":          ["PPBP", "PF4", "GP1BA", "ITGA2B", "TUBB1"],
    "Erythrocytes":       ["HBB", "HBA1", "HBA2", "GYPA", "ALAS2"],
    "Endothelial":        ["PECAM1", "VWF", "CDH5", "ENG", "CLDN5"],
    "Fibroblasts":        ["COL1A1", "COL3A1", "ACTA2", "FAP", "THY1"],
    "Epithelial":         ["EPCAM", "KRT8", "KRT18", "CDH1", "MUC1"],
    "Tumor cells":        ["TP53", "MKI67", "TOP2A", "CDK1", "PCNA", "CDKN2A"],
    "Macrophages":        ["CD68", "CD163", "MRC1", "MSR1", "C1QA", "APOE"],
    "Neutrophils":        ["FCGR3B", "CEACAM8", "S100A8", "CSF3R", "CXCR2"],
}


def score_marker_genes(adata, ctrl_size: int = 50, score_threshold: float = 0.0):
    """
    Score each cell against canonical marker gene sets using sc.tl.score_genes.
    Assigns 'cell_type' based on the highest-scoring marker set.
    Returns adata with score columns + 'cell_type' column.
    """
    present_sets = {}
    for cell_type, markers in CANONICAL_MARKERS.items():
        present = [g for g in markers if g in adata.var_names]
        if len(present) >= 2:
            present_sets[cell_type] = present

    if not present_sets:
        raise ValueError("No canonical marker genes found in this dataset's gene names.")

    score_cols = []
    for cell_type, genes in present_sets.items():
        col = f"score_{cell_type.replace(' ', '_')}"
        sc.tl.score_genes(adata, gene_list=genes, score_name=col,
                          ctrl_size=min(ctrl_size, adata.n_vars - len(genes) - 1))
        score_cols.append((cell_type, col))

    # Assign cell type = argmax across all score columns
    score_df = pd.DataFrame(
        {ct: adata.obs[col] for ct, col in score_cols},
        index=adata.obs_names
    )
    adata.obs["cell_type"] = score_df.idxmax(axis=1).astype(str)
    adata.obs["annotation_score"] = score_df.max(axis=1)
    # Mark low-confidence cells
    if score_threshold > 0:
        mask = adata.obs["annotation_score"] < score_threshold
        adata.obs.loc[mask, "cell_type"] = "Unassigned"

    adata.uns["marker_scores"] = score_df
    return adata


def annotate_cells(adata, model_name=CELLTYPIST_MODEL, majority_voting=True):
    """Run CellTypist automatic cell type annotation."""
    import numpy as np
    from scipy.sparse import issparse

    adata_norm = adata.copy()
    sc.pp.normalize_total(adata_norm, target_sum=1e4)
    sc.pp.log1p(adata_norm)

    # Fill any NaN/Inf values — CellTypist's LogisticRegression rejects them
    if issparse(adata_norm.X):
        adata_norm.X.data = np.nan_to_num(adata_norm.X.data, nan=0.0, posinf=0.0, neginf=0.0)
    else:
        adata_norm.X = np.nan_to_num(adata_norm.X, nan=0.0, posinf=0.0, neginf=0.0)

    model = celltypist.models.Model.load(model=model_name)
    predictions = celltypist.annotate(
        adata_norm, model=model, majority_voting=majority_voting,
    )

    # predicted_labels is a DataFrame; column name depends on majority_voting
    label_col = "majority_voting" if majority_voting and "majority_voting" in predictions.predicted_labels.columns \
        else "predicted_labels"
    adata.obs["cell_type"] = predictions.predicted_labels[label_col].astype(str).values

    # Confidence = max probability across all cell types for each cell
    try:
        conf = predictions.probability_matrix.max(axis=1).values
        adata.obs["cell_type_conf"] = conf.astype(float)
    except Exception:
        adata.obs["cell_type_conf"] = 1.0  # fallback

    return adata


def manual_annotate(adata, cluster_map: dict):
    """Apply a user-defined cluster → cell type mapping. Bug-safe for Categorical columns."""
    # Convert leiden to plain string to avoid Categorical constraint errors
    leiden_str = adata.obs["leiden"].astype(str)
    mapped = leiden_str.map(cluster_map)
    adata.obs["cell_type"] = mapped.fillna("Unknown").astype(str)
    return adata


def get_cluster_marker_scores(adata) -> pd.DataFrame:
    """Return per-cluster mean score for each canonical cell type."""
    if "marker_scores" not in adata.uns:
        return pd.DataFrame()
    score_df = adata.uns["marker_scores"].copy()
    score_df["cluster"] = adata.obs["leiden"].astype(str).values
    return score_df.groupby("cluster").mean().T

