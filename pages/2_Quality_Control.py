import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from core.qc import compute_qc_metrics, run_qc_filter, get_qc_stats
from utils.visualization import violin_qc
from utils.styles import inject_global_css, page_header, render_sidebar, render_nav_buttons, show_guidance, PLOTLY_TEMPLATE
from utils.interpretation import show_explanation_button, interpret_qc_metrics, show_data_quality_warnings, is_beginner_mode, show_mode_tip
from config import QC_MIN_GENES, QC_MAX_GENES, QC_MIN_CELLS, QC_MAX_MITO_PCT

st.set_page_config(page_title="Quality Control", layout="wide")
inject_global_css()
render_sidebar()

_qc_col, _qc_img = st.columns([3, 1])
with _qc_col:
    page_header(
        "🔬", "Quality Control",
        "Filter low-quality cells and genes before downstream analysis"
    )
show_guidance("quality_control")
with _qc_img:
    st.markdown("""<div style="border-radius:12px;overflow:hidden;border:1px solid #21262D;height:95px;margin-top:4px;">
    <img src="https://images.unsplash.com/photo-1559757175-5700dde675bc?w=400&q=80"
        style="width:100%;height:100%;object-fit:cover;opacity:0.65;" alt="lab quality control"/>
    </div>""", unsafe_allow_html=True)

adata = st.session_state.get("adata")
if adata is None:
    st.warning("⚠️ Please upload a dataset first (Step 1).")
    st.stop()

# Compute QC metrics if not already done
if "pct_counts_mt" not in adata.obs.columns:
    with st.spinner("Computing QC metrics..."):
        adata = compute_qc_metrics(adata)
        st.session_state["adata"] = adata

# ── Parameters ───────────────────────────────────────────────────────────────
st.markdown("### ⚙️ Filter Thresholds")

if is_beginner_mode():
    st.markdown("**Beginner Mode**: Using recommended preset thresholds (expert mode allows customization)")
    min_genes = QC_MIN_GENES
    max_genes = QC_MAX_GENES
    min_cells = QC_MIN_CELLS
    max_mito = QC_MAX_MITO_PCT
    remove_doublets = False
    show_mode_tip("These defaults work well for typical scRNA-seq datasets. Adjust in Expert mode if needed.")
else:
    c1, c2, c3, c4 = st.columns(4)
    min_genes = c1.number_input("Min genes / cell", value=QC_MIN_GENES, min_value=0, step=50)
    max_genes = c2.number_input("Max genes / cell", value=QC_MAX_GENES, min_value=100, step=100)
    min_cells = c3.number_input("Min cells / gene", value=QC_MIN_CELLS, min_value=1)
    max_mito  = c4.slider("Max % mitochondrial", 0.0, 50.0, QC_MAX_MITO_PCT, step=0.5)
    remove_doublets = st.checkbox(
        "Run doublet detection (Scrublet)",
        value=False,
        help="Recommended for droplet data; requires the 'scrublet' package.",
    )

# ── Pre-filter metrics ───────────────────────────────────────────────────────
st.markdown("### 📊 Current QC Distributions")

# Show data quality warnings and interpretations
show_data_quality_warnings(adata)

# Interpretation of current QC metrics
with st.expander("📖 Interpret Your QC Metrics", expanded=False):
    qc_interpretations = interpret_qc_metrics(adata)
    for metric, interpretation in qc_interpretations.items():
        st.markdown(interpretation)

fig_row1_c1, fig_row1_c2, fig_row1_c3 = st.columns(3)

with fig_row1_c1:
    fig = px.histogram(adata.obs, x="n_genes_by_counts", nbins=80,
                       title="Genes per Cell",
                       labels={"n_genes_by_counts": "# Unique Genes"},
                       color_discrete_sequence=["#00D4FF"],
                       template=PLOTLY_TEMPLATE)
    fig.add_vline(x=min_genes, line_dash="dash", line_color="#FF6B6B", annotation_text="min")
    fig.add_vline(x=max_genes, line_dash="dash", line_color="#FFD43B", annotation_text="max")
    fig.update_layout(paper_bgcolor="#0E1117", plot_bgcolor="#161B22")
    st.plotly_chart(fig, use_container_width=True)

with fig_row1_c2:
    fig = px.histogram(adata.obs, x="total_counts", nbins=80,
                       title="Total UMI Counts per Cell",
                       labels={"total_counts": "Total Counts"},
                       color_discrete_sequence=["#A855F7"],
                       template=PLOTLY_TEMPLATE)
    fig.update_layout(paper_bgcolor="#0E1117", plot_bgcolor="#161B22")
    st.plotly_chart(fig, use_container_width=True)

with fig_row1_c3:
    if "pct_counts_mt" in adata.obs.columns:
        fig = px.histogram(adata.obs, x="pct_counts_mt", nbins=80,
                           title="% Mitochondrial Counts",
                           labels={"pct_counts_mt": "% MT"},
                           color_discrete_sequence=["#FF6B6B"],
                           template=PLOTLY_TEMPLATE)
        fig.add_vline(x=max_mito, line_dash="dash", line_color="#FF6B6B",
                      annotation_text="threshold")
        fig.update_layout(paper_bgcolor="#0E1117", plot_bgcolor="#161B22")
        st.plotly_chart(fig, use_container_width=True)

# Scatter: genes vs counts coloured by mito %
if "pct_counts_mt" in adata.obs.columns:
    fig_sc = px.scatter(
        adata.obs.sample(min(5000, len(adata.obs))),
        x="total_counts", y="n_genes_by_counts",
        color="pct_counts_mt", color_continuous_scale="RdYlGn_r",
        opacity=0.5, template=PLOTLY_TEMPLATE,
        title="Counts vs Genes (coloured by % MT)",
        labels={"total_counts": "Total Counts", "n_genes_by_counts": "# Genes",
                "pct_counts_mt": "% MT"},
    )
    fig_sc.update_traces(marker=dict(size=3))
    fig_sc.update_layout(paper_bgcolor="#0E1117", plot_bgcolor="#161B22")
    st.plotly_chart(fig_sc, use_container_width=True)

# ── Run button ───────────────────────────────────────────────────────────────
st.divider()
if st.button("▶ Run Quality Control Filter", type="primary"):
    try:
        with st.spinner("Filtering cells and genes..."):
            adata_qc = run_qc_filter(
                adata,
                min_genes=min_genes,
                max_genes=max_genes,
                min_cells=min_cells,
                max_mito=max_mito,
                remove_doublets=remove_doublets,
            )
            st.session_state["adata"] = adata_qc
            st.session_state.setdefault("pipeline_status", {})["QC"] = "done"
    except Exception:
        st.error("Something went wrong during processing. Please try a smaller dataset.")
        st.stop()

    summary = adata_qc.uns.get("qc_summary", {})
    removed = summary.get("cells_removed", 0)
    total = summary.get("cells_before", adata.n_obs)

    st.success(f"✅ QC complete — **{removed:,}** cells removed ({removed/total*100:.1f}%)")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cells before", f"{summary.get('cells_before', 0):,}")
    c2.metric("Cells after",  f"{summary.get('cells_after', 0):,}")
    c3.metric("Removed",      f"{removed:,}")
    c4.metric("Genes remaining", f"{adata_qc.n_vars:,}")
    if remove_doublets:
        st.caption(f"Doublets removed: {adata_qc.uns.get('qc_summary', {}).get('doublets_removed', 0):,}")

    stats = get_qc_stats(adata_qc)
    st.markdown("#### Post-QC Statistics")
    stats_df = pd.DataFrame([stats]).T.reset_index()
    stats_df.columns = ["Metric", "Value"]
    stats_df["Value"] = stats_df["Value"].apply(lambda x: f"{x:,.1f}")
    import pandas as pd
    st.dataframe(stats_df, use_container_width=True)

    # Interpret the QC results
    st.divider()
    st.markdown("### 🔍 What Does This Mean?")
    with st.expander("📖 Interpretation of Your Results", expanded=True):
        st.markdown(f"""
        **Quality Control Summary:**

        You've successfully filtered your dataset:
        - **Removed {removed:,} cells** ({removed/total*100:.1f}% of original)
        - **Retained {summary.get('cells_after', 0):,} cells** of high quality
        - **Kept {adata_qc.n_vars:,} genes** expressed in at least {min_cells} cells

        **What this means:**
        - Lower cell counts suggest stricter QC thresholds
        - Keeping ~60-90% of cells is typical and healthy
        - You've eliminated low-quality cells that would confound downstream analysis

        **Next steps:**
        1. Review the QC metrics above
        2. If too many cells removed → relax thresholds and re-run
        3. If satisfied → Proceed to Step 3 (Clustering) to identify cell populations
        """)

    show_explanation_button("qc", adata_qc, button_key="qc_post")

render_nav_buttons(3)
