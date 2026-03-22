"""
Rule-based interpretation layer for scRNA-seq analysis results.
Provides educational explanations for analysis outputs without external APIs.
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional


# ── User Mode Helpers ──────────────────────────────────────────────────────────

def is_expert_mode() -> bool:
    """Check if user is in Expert mode."""
    return st.session_state.get("user_mode", "beginner") == "expert"

def is_beginner_mode() -> bool:
    """Check if user is in Beginner mode."""
    return st.session_state.get("user_mode", "beginner") == "beginner"

def show_advanced_options(label: str = "⚙️ Advanced Parameters") -> bool:
    """
    Display advanced options in an expander (only for expert mode).
    Returns True if options should be shown.

    Usage:
        if show_advanced_options():
            with st.expander(label):
                # Add advanced options here
    """
    if is_expert_mode():
        return True
    return False

def create_beginner_parameter(label: str, widget_func, *args, **kwargs):
    """
    Wrapper for creating parameters that adapt based on user mode.
    In Beginner mode: shows simple version with reduced options
    In Expert mode: shows full version with all options

    Example:
        resolution = create_beginner_parameter(
            "Resolution",
            st.slider,
            min_value=0.1,
            max_value=2.0,
            value=0.5,
            beginner_max=1.5,
            beginner_value=0.5
        )
    """
    if is_beginner_mode():
        # Modify kwargs for simpler beginner experience
        if "max_value" in kwargs:
            kwargs["max_value"] = kwargs.pop("beginner_max", kwargs["max_value"])
        if "value" in kwargs:
            original_value = kwargs["value"]
            kwargs["value"] = kwargs.pop("beginner_value", original_value)
        if "step" in kwargs and isinstance(kwargs.get("step"), float):
            kwargs["step"] = max(kwargs["step"], 0.1)  # Fewer steps for beginner

    return widget_func(*args, **kwargs)

def show_mode_tip(tip_text: str) -> None:
    """
    Display a tip specific to the current user mode.

    Example:
        show_mode_tip("Tip: Use default parameters for best results!")
    """
    if is_beginner_mode():
        st.info(f"💡 Beginner Tip: {tip_text}")
    else:
        st.caption(f"🔧 Expert Note: {tip_text}")


# ── QC Metrics Interpretation ──────────────────────────────────────────────────

def interpret_qc_metrics(adata) -> Dict[str, str]:
    """
    Interpret quality control metrics with biological context.

    Returns:
        Dictionary with interpretation for each QC metric
    """
    interpretations = {}

    # Cell count interpretation
    n_cells = adata.n_obs
    if n_cells < 100:
        interpretations["cell_count"] = (
            "⚠️ **Very small dataset** (< 100 cells). Results may have high variance. "
            "Consider combining replicates or running with caution."
        )
    elif n_cells < 1000:
        interpretations["cell_count"] = (
            "📊 **Small dataset** (100-1k cells). Sufficient for basic analysis but "
            "statistical power is limited. More cells improve result robustness."
        )
    elif n_cells < 10000:
        interpretations["cell_count"] = (
            "✅ **Good dataset size** (1k-10k cells). Typical for scRNA-seq studies. "
            "Adequate for most downstream analyses."
        )
    else:
        interpretations["cell_count"] = (
            "🎯 **Large dataset** (10k+ cells). Excellent resolution. "
            "Can detect rare cell types and subtle gene expression patterns."
        )

    # Gene count interpretation
    n_genes = adata.n_vars
    if n_genes < 10000:
        interpretations["gene_count"] = (
            "⚠️ **Limited gene coverage** (< 10k genes). May be due to filtering "
            "or shallow sequencing. Reduces pathway inference power."
        )
    elif n_genes < 20000:
        interpretations["gene_count"] = (
            "✅ **Standard gene coverage** (10k-20k genes). Typical after QC filtering. "
            "Sufficient for most analyses."
        )
    else:
        interpretations["gene_count"] = (
            "🎯 **Deep gene coverage** (20k+ genes). Excellent for detecting subtle "
            "expression changes and low-abundance transcripts."
        )

    # Mitochondrial percentage
    if "pct_counts_mt" in adata.obs.columns:
        mt_median = adata.obs["pct_counts_mt"].median()
        if mt_median > 15:
            interpretations["mito"] = (
                f"⚠️ **High mitochondrial %** ({mt_median:.1f}%). Suggests many stressed/dying cells. "
                "Consider stricter filtering (threshold < 10%)."
            )
        elif mt_median > 8:
            interpretations["mito"] = (
                f"✅ **Good mitochondrial %** ({mt_median:.1f}%). Indicates viable, healthy cells. "
                "Current filtering is appropriate."
            )
        else:
            interpretations["mito"] = (
                f"🎯 **Excellent mitochondrial %** ({mt_median:.1f}%). Very low stress markers. "
                "Dataset is of high quality."
            )

    # Gene count per cell
    if "n_counts" in adata.obs.columns:
        median_counts = adata.obs["n_counts"].median()
        mean_counts = adata.obs["n_counts"].mean()
        if median_counts < 1000:
            interpretations["counts"] = (
                f"⚠️ **Low UMI counts** (median: {median_counts:.0f}). May reduce power to detect "
                "genes. Consider deeper sequencing if possible."
            )
        elif median_counts < 5000:
            interpretations["counts"] = (
                f"✅ **Moderate UMI depth** (median: {median_counts:.0f}). Typical for 10X or similar. "
                "Good balance of cost and coverage."
            )
        else:
            interpretations["counts"] = (
                f"🎯 **Deep UMI coverage** (median: {median_counts:.0f}). Excellent sequencing depth. "
                "High sensitivity for lowly expressed genes."
            )

    return interpretations


# ── Cluster Interpretation ─────────────────────────────────────────────────────

def interpret_clusters(adata, cluster_col: str = "leiden") -> Dict[int, str]:
    """
    Generate biological interpretation for each cluster.

    Args:
        adata: AnnData object with clusters
        cluster_col: Column name containing cluster assignments

    Returns:
        Dictionary mapping cluster ID to interpretation
    """
    interpretations = {}

    if cluster_col not in adata.obs.columns:
        return interpretations

    clusters = adata.obs[cluster_col].unique()
    n_clusters = len(clusters)

    if n_clusters < 5:
        population_type = "a few major populations"
    elif n_clusters < 10:
        population_type = "distinct populations"
    elif n_clusters < 20:
        population_type = "fine-grained subpopulations"
    else:
        population_type = "very detailed subpopulations"

    for cluster in sorted(clusters):
        cluster_size = (adata.obs[cluster_col] == cluster).sum()
        pct = 100 * cluster_size / adata.n_obs

        interpretations[cluster] = (
            f"**Cluster {cluster}** ({cluster_size} cells, {pct:.1f}%)\n"
            f"This represents {population_type}. "
            f"Run step 4 (Cell Type Annotation) to identify cell types in this cluster."
        )

    return interpretations


# ── Cell Type Annotation Interpretation ────────────────────────────────────────

def interpret_cell_types(adata, annotation_col: str = "cell_type") -> Dict[str, str]:
    """
    Interpret cell type annotations with confidence information.

    Args:
        adata: AnnData object with cell type annotations
        annotation_col: Column name containing cell types

    Returns:
        Dictionary with interpretation for each cell type
    """
    interpretations = {}

    if annotation_col not in adata.obs.columns:
        return interpretations

    cell_types = adata.obs[annotation_col].value_counts()

    for cell_type, count in cell_types.items():
        if pd.isna(cell_type) or cell_type == "Unknown":
            continue

        pct = 100 * count / adata.n_obs

        if count < 10:
            confidence = "⚠️ Rare (< 10 cells)"
        elif count < 50:
            confidence = "📊 Uncommon (10-50 cells)"
        elif count < 200:
            confidence = "✅ Common (50-200 cells)"
        else:
            confidence = "🎯 Abundant (200+ cells)"

        interpretations[cell_type] = (
            f"**{cell_type}** - {count} cells ({pct:.1f}%)\n"
            f"{confidence}. "
            f"Use this population for differential expression or pathway analysis."
        )

    return interpretations


# ── Differential Expression Interpretation ─────────────────────────────────────

def interpret_de_result(de_df: pd.DataFrame, comparison: str,
                       top_n: int = 5) -> str:
    """
    Interpret differential expression results with biological context.

    Args:
        de_df: DataFrame with DE results (must have 'names', 'logfoldchanges', 'pvals_adj')
        comparison: Description of the comparison (e.g., "Cluster 0 vs Rest")
        top_n: Number of top genes to highlight

    Returns:
        Markdown-formatted interpretation string
    """
    if de_df.empty:
        return "❌ No significant genes found at this threshold."

    interpretation = f"### 🔬 Interpretation: {comparison}\n\n"

    # Overall pattern
    upregulated = (de_df["logfoldchanges"] > 0).sum()
    downregulated = (de_df["logfoldchanges"] < 0).sum()
    total = len(de_df)

    interpretation += f"**Overall Pattern:** {upregulated} upregulated, {downregulated} downregulated genes\n\n"

    # Top genes
    if len(de_df) > 0:
        interpretation += f"**Top {min(top_n, len(de_df))} Marker Genes:**\n"
        top_genes = de_df.nlargest(top_n, "logfoldchanges") if upregulated > 0 else de_df.nsmallest(top_n, "logfoldchanges")
        for idx, (_, row) in enumerate(top_genes.iterrows(), 1):
            gene_name = row.get("names", f"Gene_{idx}")
            lfc = row.get("logfoldchanges", 0)
            pval = row.get("pvals_adj", 1.0)

            if lfc > 0:
                direction = "⬆️ UP"
            else:
                direction = "⬇️ DOWN"

            interpretation += f"{idx}. **{gene_name}** {direction} (log2FC: {lfc:.2f}, p-adj: {pval:.2e})\n"

    interpretation += "\n**Next Step:** Run Pathway Enrichment on these genes to understand biological functions."

    return interpretation


# ── Pathway Enrichment Interpretation ──────────────────────────────────────────

def interpret_pathway_results(pathway_df: pd.DataFrame,
                             cell_type: str = "") -> str:
    """
    Interpret pathway enrichment results with biological context.

    Args:
        pathway_df: DataFrame with pathway results (must have 'Term', 'Adjusted P-value')
        cell_type: Cell type being analyzed (for context)

    Returns:
        Markdown-formatted interpretation string
    """
    if pathway_df.empty:
        return "❌ No significant pathways found. May need to adjust statistical thresholds."

    interpretation = "### 🧬 Biological Interpretation\n\n"

    # Summarize top pathways
    significant = (pathway_df.get("Adjusted P-value", pathway_df.get("p_adjust", pathway_df.get("p_value", 1.0))) < 0.05).sum()

    interpretation += f"**Found {significant} significant pathways** enriched in this dataset.\n\n"

    # Categorize pathways
    top_pathways = pathway_df.head(5)
    interpretation += "**Top Enriched Pathways:**\n"
    for idx, (_, row) in enumerate(top_pathways.iterrows(), 1):
        term = row.get("Term", f"Pathway_{idx}")
        pval = row.get("Adjusted P-value", row.get("p_adjust", row.get("p_value", 1.0)))

        # Suggest biological interpretation
        if "immune" in term.lower() or "immune" in term.lower():
            bio_type = "🛡️ Immune"
        elif "cell cycle" in term.lower() or "proliferation" in term.lower():
            bio_type = "🔄 Proliferation"
        elif "apoptosis" in term.lower() or "death" in term.lower():
            bio_type = "💀 Cell Death"
        elif "metabolism" in term.lower():
            bio_type = "⚡ Metabolism"
        elif "signaling" in term.lower():
            bio_type = "📡 Signaling"
        else:
            bio_type = "📊 Function"

        interpretation += f"{idx}. **{bio_type} - {term}** (p-adj: {pval:.2e})\n"

    if cell_type:
        interpretation += f"\n**Cell Type Context:** These pathways are enriched in {cell_type}. "
        interpretation += "Consider what biological role this cell type plays and whether pathway activity aligns."

    return interpretation


# ── Generic "What does this mean?" function ────────────────────────────────────

def explain_result(result_type: str, data=None, **kwargs) -> str:
    """
    Generate explanation for any analysis result.

    Args:
        result_type: Type of result ('qc', 'cluster', 'celltype', 'de', 'pathway')
        data: Relevant data (adata, dataframe, etc.)
        **kwargs: Additional parameters for specific interpretations

    Returns:
        Markdown-formatted explanation string
    """
    explanations = {
        "qc": "Quality control assesses whether cells are viable and data is of high quality. "
              "Filters remove dead cells (high mitochondrial %), low-quality cells (few genes), "
              "and background. Good QC is essential for downstream analysis.",

        "cluster": "Clustering groups similar cells together based on expression patterns. "
                  "Each cluster likely represents a distinct cell state or type. "
                  "The number of clusters depends on resolution—higher = more fine-grained.",

        "celltype": "Cell type annotation assigns biological identity to clusters. "
                   "AI-powered methods (CellTypist) use marker genes from known databases. "
                   "Always validate with your own knowledge of expected cell types.",

        "de": "Differential expression finds genes that differ between cell groups. "
             "Positive log-fold change = upregulated; negative = downregulated. "
             "These genes are potential markers or functional drivers.",

        "pathway": "Pathway analysis identifies biological processes enriched in your data. "
                  "Tests if genes in known pathways are significantly co-expressed. "
                  "Helps understand functions of cell types and disease mechanisms.",

        "umap": "UMAP is a visualization technique that reduces high-dimensional gene expression "
               "to 2D while preserving local structure. Cells close together have similar expression. "
               "Used to visualize clusters and cell types.",

        "volcano": "Volcano plots show differential expression results. "
                  "X-axis = log2 fold change (effect size). Y-axis = -log10(p-value) (significance). "
                  "Top-left/right = significant changes with large effect sizes."
    }

    base_explanation = explanations.get(result_type, "Run this analysis to explore your data.")

    # Add specific interpretations if data provided
    if result_type == "qc" and data is not None:
        qc_interp = interpret_qc_metrics(data)
        specific = "\n\n**Your Dataset:**\n" + "\n".join(f"- {v}" for v in qc_interp.values())
        return base_explanation + specific

    elif result_type == "cluster" and data is not None:
        cluster_col = kwargs.get("cluster_col", "leiden")
        cluster_interp = interpret_clusters(data, cluster_col)
        if cluster_interp:
            specific = "\n\n**Your Clusters:**\n" + "\n".join(cluster_interp.values())
            return base_explanation + specific

    return base_explanation


# ── Data quality warnings ──────────────────────────────────────────────────────

def get_data_quality_warnings(adata) -> List[Tuple[str, str]]:
    """
    Get context-aware warnings about data quality.

    Returns:
        List of (warning_level, message) tuples
        warning_level: 'info', 'warning', 'error'
    """
    warnings = []

    # Cell count warnings
    if adata.n_obs < 100:
        warnings.append(("error", "Very small dataset (< 100 cells). Results may be unreliable."))
    elif adata.n_obs < 500:
        warnings.append(("warning", "Small dataset (< 500 cells). Consider statistical validation."))

    # Gene count warnings
    if adata.n_vars < 2000:
        warnings.append(("warning", "Fewer than 2000 genes: Limited pathway inference power."))

    # Mitochondrial content
    if "pct_counts_mt" in adata.obs.columns:
        mt_high = (adata.obs["pct_counts_mt"] > 15).sum()
        if mt_high > len(adata) * 0.1:
            pct = 100 * mt_high / len(adata)
            warnings.append(("warning", f"{pct:.1f}% cells have high mitochondrial content (>15%). Consider stricter filtering."))

    # Sparsity
    if hasattr(adata.X, 'nnz'):  # Sparse matrix
        sparsity = 1 - (adata.X.nnz / (adata.n_obs * adata.n_vars))
        if sparsity > 0.99:
            warnings.append(("info", f"Very sparse data ({sparsity*100:.1f}% zeros). Typical for scRNA-seq but impacts some methods."))

    # Duplicates
    if adata.obs.duplicated().sum() > 0:
        warnings.append(("warning", f"{adata.obs.duplicated().sum()} potential duplicate cells detected."))

    return warnings


def get_clustering_warnings(adata, n_clusters: int = None) -> List[Tuple[str, str]]:
    """
    Get context-aware warnings about clustering results.

    Args:
        adata: AnnData object with leiden clusters
        n_clusters: Number of clusters (optional, will be computed if not provided)

    Returns:
        List of (warning_level, message) tuples
    """
    warnings = []

    if n_clusters is None and "leiden" in adata.obs.columns:
        n_clusters = adata.obs["leiden"].nunique()

    if n_clusters is None:
        return warnings

    # Too few clusters
    if n_clusters == 1:
        warnings.append(("warning", "Only 1 cluster detected! Increase resolution or check data quality."))
    elif n_clusters < 3:
        warnings.append(("info", "Few clusters detected. May indicate uniform cell population or low resolution."))

    # Too many clusters
    elif n_clusters > 30:
        warnings.append(("warning", f"Very high number of clusters ({n_clusters}). Consider lowering resolution to reduce fragmentation."))

    # Check cluster sizes
    if "leiden" in adata.obs.columns:
        cluster_sizes = adata.obs["leiden"].value_counts()
        min_size = cluster_sizes.min()
        max_size = cluster_sizes.max()

        if min_size < 3:
            warnings.append(("warning", f"Smallest cluster has only {min_size} cells. May be noise or biologically irrelevant."))

        if max_size / min_size > 100:
            warnings.append(("info", f"Cluster sizes vary widely (1:{max_size/min_size:.0f}). May reflect true biology or technical bias."))

    return warnings


def get_annotation_warnings(adata) -> List[Tuple[str, str]]:
    """
    Get context-aware warnings about cell type annotations.

    Args:
        adata: AnnData object with cell type annotations

    Returns:
        List of (warning_level, message) tuples
    """
    warnings = []

    if "cell_type" not in adata.obs.columns:
        return warnings

    # Check for unassigned cells
    unassigned = adata.obs["cell_type"].isna().sum() + (adata.obs["cell_type"] == "Unassigned").sum()
    if unassigned > 0:
        pct = 100 * unassigned / len(adata)
        if pct > 20:
            warnings.append(("warning", f"{pct:.1f}% cells are unassigned. May need different annotation method."))
        elif pct > 5:
            warnings.append(("info", f"{pct:.1f}% cells are unassigned. Acceptable for high-confidence annotation."))

    # Check for rare cell types
    cell_type_counts = adata.obs["cell_type"].value_counts()
    rare_types = (cell_type_counts < 10).sum()
    if rare_types > 0:
        warnings.append(("info", f"{rare_types} cell types have < 10 cells. May be rare populations or artifacts."))

    # Check for ambiguous annotations
    if any(adata.obs["cell_type"].astype(str).str.contains("Ambiguous")):
        n_ambiguous = (adata.obs["cell_type"].astype(str).str.contains("Ambiguous")).sum()
        warnings.append(("warning", f"{n_ambiguous} cells marked as ambiguous. Consider using consensus labels."))

    return warnings


def get_statistical_power_warnings(adata) -> List[Tuple[str, str]]:
    """
    Get warnings about statistical power based on dataset characteristics.

    Args:
        adata: AnnData object

    Returns:
        List of (warning_level, message) tuples
    """
    warnings = []

    # Check for groups small enough to cause power issues
    if "leiden" in adata.obs.columns:
        cluster_sizes = adata.obs["leiden"].value_counts()
        small_clusters = (cluster_sizes < 20).sum()
        if small_clusters > 0:
            warnings.append(("warning", f"{small_clusters} clusters have < 20 cells. Differential expression analysis may lack power."))

    # Check for extreme imbalance
    if "cell_type" in adata.obs.columns:
        cell_type_counts = adata.obs["cell_type"].value_counts()
        if cell_type_counts.max() / cell_type_counts.min() > 1000:
            warnings.append(("warning", "Extreme cell type imbalance detected (>1000:1). May bias statistical results."))

    return warnings


def show_comprehensive_warnings(adata, context: str = "general") -> None:
    """
    Display all relevant warnings based on data and context.

    Args:
        adata: AnnData object
        context: 'general', 'qc', 'clustering', 'annotation', 'statistical'
    """
    all_warnings = []

    if context in ["general", "qc"]:
        all_warnings.extend(get_data_quality_warnings(adata))

    if context in ["general", "clustering"]:
        all_warnings.extend(get_clustering_warnings(adata))

    if context in ["general", "annotation"]:
        all_warnings.extend(get_annotation_warnings(adata))

    if context in ["general", "statistical"]:
        all_warnings.extend(get_statistical_power_warnings(adata))

    if all_warnings:
        st.markdown("**⚠️ Data Quality Notes:**")
        for level, message in all_warnings:
            if level == "error":
                st.error(f"🔴 {message}")
            elif level == "warning":
                st.warning(f"🟡 {message}")
            else:
                st.info(f"ℹ️ {message}")

def show_explanation_button(result_type: str, data=None,
                          button_key: str = None, **kwargs) -> None:
    """
    Display an expandable "What does this mean?" button with explanation.

    Args:
        result_type: Type of result to explain
        data: Relevant data for specific interpretation
        button_key: Unique key for the button (for multiple buttons on same page)
        **kwargs: Additional parameters for interpretation
    """
    if button_key is None:
        button_key = f"explain_{result_type}"

    with st.expander("❓ What does this mean?", expanded=False):
        explanation = explain_result(result_type, data, **kwargs)
        st.markdown(explanation)


def show_data_quality_warnings(adata) -> None:
    """Display data quality warnings."""
    show_comprehensive_warnings(adata, context="qc")
