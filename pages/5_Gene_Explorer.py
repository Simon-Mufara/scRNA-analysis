import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px

from core.pipeline import generate_marker_dotplot
from utils.visualization import gene_umap_plot
from utils.styles import inject_global_css, page_header, render_sidebar, render_nav_buttons, show_guidance, PALETTE, PLOTLY_TEMPLATE
from config import CLINICAL_MARKERS

st.set_page_config(page_title="Gene Explorer", layout="wide")
inject_global_css()
render_sidebar()

page_header(
    "🔍", "Gene Expression Explorer",
    "Visualize single-gene or multi-gene expression across the UMAP landscape"
)

adata = st.session_state.get("adata")
if adata is None:
    st.warning("⚠️ Please upload a dataset first (Step 1).")
    st.stop()
if "X_umap" not in adata.obsm:
    st.warning("⚠️ Run clustering (Step 3) to generate UMAP coordinates.")
    st.stop()

tab_single, tab_panel, tab_violin, tab_dotplot = st.tabs([
    "🔬 Single Gene", "🗂️ Multi-Gene Panel", "🎻 Violin Plot", "🔴 Marker Dotplot"
])

# ── Single Gene ──────────────────────────────────────────────────────────────
with tab_single:
    c1, c2 = st.columns([2, 1])
    with c1:
        gene = st.text_input("Gene symbol (e.g. CD8A, TP53, PDCD1)",
                             placeholder="Type a gene name...")
    with c2:
        st.markdown("**Quick picks — clinical markers**")
        quick_genes = ["CD8A", "CD4", "FOXP3", "PDCD1", "CD14", "MS4A1",
                       "TP53", "MKI67", "BRCA1", "EGFR", "NKG7", "GZMB"]
        btn_cols = st.columns(4)
        for i, g in enumerate(quick_genes):
            if btn_cols[i % 4].button(g, key=f"q_{g}", use_container_width=True):
                gene = g

    if gene:
        if gene in adata.var_names:
            col_umap, col_violin = st.columns([2, 1])
            with col_umap:
                fig = gene_umap_plot(adata, gene)
                if fig:
                    fig.update_layout(paper_bgcolor="#0E1117", plot_bgcolor="#161B22", height=500)
                    st.plotly_chart(fig, use_container_width=True)
            with col_violin:
                groupby = "leiden" if "leiden" in adata.obs.columns else None
                if groupby:
                    # Get expression values
                    expr = np.array(
                        adata[:, gene].X.todense() if hasattr(adata[:, gene].X, "todense")
                        else adata[:, gene].X
                    ).flatten()
                    viol_df = pd.DataFrame({
                        "Expression": expr,
                        "Cluster": adata.obs[groupby].astype(str).values
                    })
                    fig_v = px.violin(
                        viol_df, x="Cluster", y="Expression",
                        box=True, points=False,
                        title=f"{gene} by Cluster",
                        color="Cluster",
                        color_discrete_sequence=PALETTE,
                        template=PLOTLY_TEMPLATE
                    )
                    fig_v.update_layout(
                        paper_bgcolor="#0E1117", plot_bgcolor="#161B22",
                        showlegend=False, height=500
                    )
                    st.plotly_chart(fig_v, use_container_width=True)

            # Stats table
            expr = np.array(
                adata[:, gene].X.todense() if hasattr(adata[:, gene].X, "todense")
                else adata[:, gene].X
            ).flatten()
            pct_expr = (expr > 0).mean() * 100
            st.markdown(f"""
            <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:8px;">
                <span style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:8px 16px;">
                    <b style="color:#8B949E;font-size:0.75rem;">MEAN EXPR</b><br>
                    <b style="color:#00D4FF;">{np.mean(expr):.3f}</b>
                </span>
                <span style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:8px 16px;">
                    <b style="color:#8B949E;font-size:0.75rem;">MAX EXPR</b><br>
                    <b style="color:#51CF66;">{np.max(expr):.3f}</b>
                </span>
                <span style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:8px 16px;">
                    <b style="color:#8B949E;font-size:0.75rem;">% CELLS EXPRESSING</b><br>
                    <b style="color:#FFD43B;">{pct_expr:.1f}%</b>
                </span>
            </div>
            """, unsafe_allow_html=True)
        else:
            close = [v for v in adata.var_names if gene.upper() in v.upper()][:10]
            st.warning(f"Gene `{gene}` not found in dataset.")
            if close:
                st.info(f"Did you mean one of: **{', '.join(close)}**?")

# ── Multi-gene panel ──────────────────────────────────────────────────────────
with tab_panel:
    panel_input = st.text_area(
        "Enter comma-separated gene symbols",
        value="CD3D, CD8A, CD4, CD14, MS4A1, GNLY, NKG7, FCGR3A",
        height=80
    )
    cols_per_row = st.selectbox("Plots per row", [2, 3, 4], index=1)

    if st.button("▶ Generate Panel", type="primary", key="gen_panel"):
        genes = [g.strip() for g in panel_input.split(",") if g.strip()]
        found   = [g for g in genes if g in adata.var_names]
        missing = [g for g in genes if g not in adata.var_names]
        if missing:
            st.warning(f"Not found in dataset: **{', '.join(missing)}**")
        if found:
            rows = [found[i:i+cols_per_row] for i in range(0, len(found), cols_per_row)]
            for row in rows:
                rcols = st.columns(cols_per_row)
                for i, g in enumerate(row):
                    with rcols[i]:
                        fig = gene_umap_plot(adata, g)
                        if fig:
                            fig.update_layout(
                                paper_bgcolor="#0E1117", plot_bgcolor="#161B22",
                                height=320, margin=dict(t=40, b=10, l=10, r=10),
                                coloraxis_showscale=False,
                            )
                            fig.update_traces(marker=dict(size=2))
                            st.plotly_chart(fig, use_container_width=True)

# ── Violin plot ───────────────────────────────────────────────────────────────
with tab_violin:
    v_gene = st.text_input("Gene for violin", placeholder="e.g. LYZ")
    v_groupby = st.selectbox("Group by", ["leiden"] + (
        ["cell_type"] if "cell_type" in adata.obs.columns else []
    ), key="v_groupby")

    if v_gene and v_gene in adata.var_names:
        expr = np.array(
            adata[:, v_gene].X.todense() if hasattr(adata[:, v_gene].X, "todense")
            else adata[:, v_gene].X
        ).flatten()
        vdf = pd.DataFrame({
            "Expression (log-norm)": expr,
            v_groupby: adata.obs[v_groupby].astype(str).values
        })
        fig = px.violin(vdf, x=v_groupby, y="Expression (log-norm)",
                        box=True, points="outliers",
                        color=v_groupby, color_discrete_sequence=PALETTE,
                        title=f"{v_gene} Expression by {v_groupby}",
                        template=PLOTLY_TEMPLATE)
        fig.update_layout(paper_bgcolor="#0E1117", plot_bgcolor="#161B22",
                          showlegend=False, height=500)
        st.plotly_chart(fig, use_container_width=True)
    elif v_gene:
        st.warning(f"Gene `{v_gene}` not found.")

# ── Marker dotplot ────────────────────────────────────────────────────────────
with tab_dotplot:
    category = st.selectbox("Marker category", list(CLINICAL_MARKERS.keys()))
    groupby  = st.selectbox("Group by", ["leiden"] + (
        ["cell_type"] if "cell_type" in adata.obs.columns else []
    ), key="dot_groupby")

    if st.button("▶ Generate Dotplot", type="primary", key="gen_dot"):
        import matplotlib.pyplot as plt
        genes = CLINICAL_MARKERS[category]
        present = [g for g in genes if g in adata.var_names]
        if present:
            fig = generate_marker_dotplot(adata, present, groupby=groupby, color_map="viridis")
            st.pyplot(fig, use_container_width=True)
            plt.close()
        else:
            st.warning(f"None of {genes} were found in this dataset.")

render_nav_buttons(6)
