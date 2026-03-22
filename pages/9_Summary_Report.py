"""
Comprehensive Summary Report — aggregates all analysis results and provides key insights.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

from utils.styles import inject_global_css, page_header, render_sidebar, render_nav_buttons
from utils.interpretation import show_explanation_button
from utils.export import export_to_excel, export_to_csv

st.set_page_config(page_title="Summary Report", layout="wide")
inject_global_css()
render_sidebar()

page_header(
    "📋", "Comprehensive Summary Report",
    "Aggregated insights from your entire analysis pipeline"
)

adata = st.session_state.get("adata")
if adata is None:
    st.warning("⚠️ Please upload and analyze a dataset first.")
    st.stop()

# ── Build Summary ──────────────────────────────────────────────────────────────

st.markdown("## 📊 Analysis Overview")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Cells Analyzed", f"{adata.n_obs:,}")
with col2:
    st.metric("Genes Detected", f"{adata.n_vars:,}")
with col3:
    n_clusters = adata.obs.get("leiden", pd.Series()).nunique() if "leiden" in adata.obs else 0
    st.metric("Clusters Identified", f"{n_clusters:.0f}")

# ── QC Metrics Summary ─────────────────────────────────────────────────────────

st.markdown("## 🔬 Quality Control Results")
qc_cols = st.columns(4)

with qc_cols[0]:
    if "n_genes_by_counts" in adata.obs.columns:
        median_genes = adata.obs["n_genes_by_counts"].median()
        st.metric("Median Genes/Cell", f"{median_genes:,.0f}")

with qc_cols[1]:
    if "total_counts" in adata.obs.columns:
        median_counts = adata.obs["total_counts"].median()
        st.metric("Median UMI/Cell", f"{median_counts:,.0f}")

with qc_cols[2]:
    if "pct_counts_mt" in adata.obs.columns:
        median_mito = adata.obs["pct_counts_mt"].median()
        quality = "✅ Good" if median_mito < 10 else "⚠️ Elevated" if median_mito < 15 else "❌ High"
        st.metric("Mitochondrial %", f"{median_mito:.1f}% {quality}")

with qc_cols[3]:
    if "pct_counts_mt" in adata.obs.columns:
        high_mito_count = (adata.obs["pct_counts_mt"] > 15).sum()
        high_mito_pct = 100 * high_mito_count / len(adata)
        st.metric("High-MT Cells", f"{high_mito_pct:.1f}%")

# Explain what these metrics mean
with st.expander("📖 What do these QC metrics indicate?", expanded=False):
    st.markdown("""
    - **Genes/Cell**: Complexity of cell transcriptome. Lower values (< 300) suggest doublets or low quality
    - **UMI/Cell**: Total sequencing depth per cell. Higher = better sensitivity
    - **Mitochondrial %**: Stress indicator. High % (> 15%) suggests dying or stressed cells
    - **High-MT Cells**: Cells that may be artifactual and should be filtered
    """)

# ── Clustering Results ─────────────────────────────────────────────────────────

if "leiden" in adata.obs.columns:
    st.markdown("## 🗺️ Cluster Analysis")

    cluster_sizes = adata.obs["leiden"].value_counts().sort_index()
    st.metric("Number of Clusters", len(cluster_sizes))

    col_cluster_chart, col_cluster_stats = st.columns([2, 1])

    with col_cluster_chart:
        fig = px.bar(
            x=cluster_sizes.index.astype(str),
            y=cluster_sizes.values,
            labels={"x": "Cluster", "y": "# Cells"},
            title="Cluster Sizes",
            color=cluster_sizes.values,
            color_continuous_scale="Blues",
        )
        fig.update_layout(paper_bgcolor="#0E1117", plot_bgcolor="#161B22")
        st.plotly_chart(fig, use_container_width=True)

    with col_cluster_stats:
        st.markdown("**Cluster Statistics:**")
        st.markdown(f"- Min size: {cluster_sizes.min()} cells")
        st.markdown(f"- Max size: {cluster_sizes.max()} cells")
        st.markdown(f"- Mean size: {cluster_sizes.mean():.0f} cells")

# ── Cell Type Composition ──────────────────────────────────────────────────────

if "cell_type" in adata.obs.columns:
    st.markdown("## 🏷️ Cell Type Composition")

    cell_type_counts = adata.obs["cell_type"].value_counts()
    st.metric("Number of Cell Types", len(cell_type_counts))

    col_celltype_chart, col_celltype_list = st.columns([2, 1])

    with col_celltype_chart:
        fig = px.pie(
            names=cell_type_counts.index,
            values=cell_type_counts.values,
            title="Cell Type Distribution",
        )
        fig.update_layout(paper_bgcolor="#0E1117")
        st.plotly_chart(fig, use_container_width=True)

    with col_celltype_list:
        st.markdown("**Cell Type Details:**")
        for cell_type, count in cell_type_counts.items():
            pct = 100 * count / len(adata)
            st.markdown(f"- **{cell_type}**: {count:,} ({pct:.1f}%)")

# ── Differential Expression Summary ────────────────────────────────────────────

if "rank_genes_groups" in adata.uns:
    st.markdown("## 🔬 Marker Gene Summary")

    rgg = adata.uns.get("rank_genes_groups", {})
    key = rgg.get("names", None)

    # Check if key exists and is not empty (works with numpy arrays and dicts)
    if key is not None and len(key) > 0:
        # Show top markers across all groups
        st.markdown("Top differentially expressed genes (by group):")

        marker_summary = []

        # Handle both dict-like and array-like structures
        if isinstance(key, dict):
            groups_to_show = list(key.keys())[:5]
            for group in groups_to_show:
                if isinstance(key[group], dict):
                    genes = list(key[group].keys())[:3]
                else:
                    genes = list(key[group])[:3]
                marker_summary.append(f"- **{group}**: {', '.join(str(g) for g in genes)}")
        else:
            # Handle numpy array structure from rank_genes_groups
            try:
                # For numpy structured arrays, iterate through field names
                groups_to_show = list(key.dtype.names)[:5] if hasattr(key, 'dtype') else []
                for group in groups_to_show:
                    genes = list(key[group][:3])
                    marker_summary.append(f"- **{group}**: {', '.join(str(g) for g in genes)}")
            except (AttributeError, TypeError):
                # Fallback: just show that data exists
                marker_summary = ["Marker gene data available (complex format)"]

        st.markdown("\n".join(marker_summary))

        with st.expander("📖 Understanding Marker Genes", expanded=False):
            st.markdown("""
            Marker genes are genes that distinguish each cell type/cluster from others.
            - High expression in your cell type = good markers
            - These are useful for: validation, identifying cell types, finding drug targets
            """)

# ── Pathway Summary ────────────────────────────────────────────────────────────

if "pathway_results" in st.session_state:
    st.markdown("## 🧪 Enriched Pathways Summary")

    pathway_df = st.session_state["pathway_results"]
    sig_pathways = (pathway_df.get("Adjusted P-value", 1.0) < 0.05).sum()

    st.metric("Significant Pathways", f"{sig_pathways}")

    if len(pathway_df) > 0:
        top_pathways = pathway_df.head(10)
        st.markdown("**Top Enriched Pathways:**")
        for idx, row in top_pathways.iterrows():
            term = row.get("Term", "Unknown")
            pval = row.get("Adjusted P-value", 1.0)
            st.markdown(f"✓ {term} (p={pval:.2e})")

# ── Data Quality Summary ───────────────────────────────────────────────────────

st.markdown("## ⚠️ Data Quality Notes")

notes = []

# Check dataset size
if adata.n_obs < 500:
    notes.append("⚠️ **Small dataset** (< 500 cells): Results should be validated with independent cohort")
elif adata.n_obs > 100000:
    notes.append("✅ **Very large dataset** (100k+ cells): Excellent statistical power")

# Check gene coverage
if adata.n_vars < 5000:
    notes.append("⚠️ **Limited gene coverage** (< 5k genes): May impact pathway analysis")

# Check mitochondrial content
if "pct_counts_mt" in adata.obs.columns:
    high_mt_pct = 100 * (adata.obs["pct_counts_mt"] > 15).sum() / len(adata)
    if high_mt_pct > 20:
        notes.append(f"⚠️ **{high_mt_pct:.1f}% high-MT cells**: Consider re-running QC with stricter thresholds")

# Check for very small clusters
if "leiden" in adata.obs.columns:
    min_cluster_size = adata.obs["leiden"].value_counts().min()
    if min_cluster_size < 5:
        notes.append("⚠️ **Very small clusters** detected: May be artifacts, consider higher resolution")

if notes:
    for note in notes:
        st.info(note)
else:
    st.success("✅ Dataset appears to be of good quality!")

# ── Export Summary ─────────────────────────────────────────────────────────────

st.divider()
st.markdown("## 💾 Export Results")

# Create summary dataframe
summary_data = {
    "Metric": [
        "Cells Analyzed",
        "Genes Detected",
        "Clusters Identified",
        "Cell Types",
        "Analysis Date",
        "QC Status",
    ],
    "Value": [
        str(adata.n_obs),
        str(adata.n_vars),
        str(n_clusters if n_clusters > 0 else "N/A"),
        str(adata.obs.get("cell_type", pd.Series()).nunique() if "cell_type" in adata.obs else "N/A"),
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        "High Quality" if not notes else "Review Recommended",
    ],
}

summary_df = pd.DataFrame(summary_data)

col_download1, col_download2 = st.columns(2)

# CSV export using proper formatting
csv_bytes = export_to_csv(summary_df)
col_download1.download_button(
    "⬇️ Download Summary (CSV)",
    data=csv_bytes,
    file_name="analysis_summary.csv",
    mime="text/csv",
)

# Excel export with sheet 1: Summary
xlsx_bytes = export_to_excel(
    summary_df,
    sheet_name="Summary",
    numeric_cols=[]
)
col_download2.download_button(
    "⬇️ Download Summary (Excel)",
    data=xlsx_bytes,
    file_name="analysis_summary.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# ── Next Steps ─────────────────────────────────────────────────────────────────

st.divider()
st.markdown("## 📍 Next Steps")

col_next1, col_next2 = st.columns(2)

with col_next1:
    st.markdown("""
    **Quality Assurance:**
    - ✓ Review QC metrics above
    - ✓ Validate cell type identities
    - ✓ Check marker genes in literature
    """)

with col_next2:
    st.markdown("""
    **Publication & Sharing:**
    - → Generate PDF Clinical Report (Step 7)
    - → Create Team Summary (Step 8)
    - → Export all results for manuscript
    """)

# Navigation
render_nav_buttons(10)
