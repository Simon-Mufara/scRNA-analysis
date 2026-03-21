import streamlit as st
import plotly.express as px
import pandas as pd

from core.clustering import run_clustering_step
from utils.visualization import umap_plot
from utils.styles import inject_global_css, page_header, render_sidebar, render_nav_buttons, PALETTE, PLOTLY_TEMPLATE
from config import N_TOP_GENES, N_PCS, N_NEIGHBORS, LEIDEN_RESOLUTION

st.set_page_config(page_title="Clustering & UMAP", layout="wide")
inject_global_css()
render_sidebar()

_cl_col, _cl_img = st.columns([3, 1])
with _cl_col:
    page_header(
        "📊", "Normalization, Dimensionality Reduction & Clustering",
        "Normalize → HVG selection → PCA → UMAP → Leiden community detection"
    )
with _cl_img:
    st.markdown("""<div style="border-radius:12px;overflow:hidden;border:1px solid #21262D;height:95px;margin-top:4px;">
    <img src="https://images.unsplash.com/photo-1628595351029-c2bf17511435?w=400&q=80"
        style="width:100%;height:100%;object-fit:cover;opacity:0.65;" alt="data clustering"/>
    </div>""", unsafe_allow_html=True)

adata = st.session_state.get("adata")
if adata is None:
    st.warning("⚠️ Please upload a dataset first (Step 1).")
    st.stop()

# ── Parameters ───────────────────────────────────────────────────────────────
with st.expander("⚙️ Pipeline Parameters", expanded=True):
    c1, c2, c3, c4 = st.columns(4)
    n_top   = c1.number_input("Top variable genes", value=N_TOP_GENES, step=100,
                               help="Highly variable genes used for PCA")
    n_pcs   = c2.number_input("# PCs", value=N_PCS, min_value=10, max_value=100,
                               help="Principal components for neighbour graph")
    n_nb    = c3.number_input("# Neighbours", value=N_NEIGHBORS, min_value=5, max_value=100)
    res     = c4.slider("Leiden resolution", 0.1, 2.0, LEIDEN_RESOLUTION, step=0.1,
                        help="Higher = more clusters")
    c5, c6 = st.columns(2)
    integration_method = c5.selectbox(
        "Batch integration",
        ["none", "harmony", "bbknn", "scanorama"],
        help="Use when you have batch effects and a batch metadata column.",
    )
    batch_candidates = [""] + list(adata.obs.columns)
    batch_key = c6.selectbox(
        "Batch key column",
        batch_candidates,
        help="Metadata column identifying batch/study/source.",
    )

if st.button("▶ Run Full Clustering Pipeline", type="primary"):
    steps = ["Normalizing", "Log1p transform", "HVG selection", "PCA",
             "Building neighbour graph", "UMAP", "Leiden clustering"]
    prog = st.progress(0, text="Starting pipeline...")
    for i, step in enumerate(steps):
        prog.progress((i + 1) / len(steps), text=f"{step}...")

    try:
        with st.spinner("Running clustering pipeline..."):
            adata = run_clustering_step(
                adata,
                n_top_genes=n_top,
                n_pcs=n_pcs,
                n_neighbors=n_nb,
                resolution=res,
                integration_method=integration_method,
                batch_key=batch_key,
            )
            st.session_state["adata"] = adata
            st.session_state.setdefault("pipeline_status", {})["Clustering"] = "done"

        prog.progress(1.0, text="Done!")
        n_clusters = adata.obs["leiden"].nunique()
        st.success(f"✅ Pipeline complete — **{n_clusters} clusters** identified")
    except Exception:
        prog.progress(1.0, text="Failed")
        st.error("Something went wrong during processing. Please try a smaller dataset.")

# ── UMAP visualization ───────────────────────────────────────────────────────
if "X_umap" not in (adata.obsm if adata is not None else {}):
    st.info("Run the clustering pipeline above to generate UMAP coordinates.")
    st.stop()

if "leiden" not in adata.obs.columns:
    st.warning("⚠️ Leiden clusters not found. Run the clustering pipeline to generate clusters.")
    st.stop()

st.divider()
st.markdown("### 🗺️ UMAP Explorer")

col_ctrl, col_umap = st.columns([1, 3])

with col_ctrl:
    color_options = ["leiden"]
    if "cell_type" in adata.obs.columns:
        color_options.insert(0, "cell_type")
    # Add numeric obs columns
    num_cols = adata.obs.select_dtypes("number").columns.tolist()
    color_options += [c for c in num_cols if c not in color_options]

    st.session_state.setdefault("umap_color_by", color_options[0] if color_options else "leiden")
    st.session_state.setdefault("umap_pt_size", 3)
    st.session_state.setdefault("umap_pt_opacity", 0.75)
    st.session_state.setdefault("umap_apply_nonce", 0)
    with st.form("umap_view_controls", clear_on_submit=False):
        color_by = st.selectbox("Color by", color_options, index=color_options.index(st.session_state["umap_color_by"]) if st.session_state["umap_color_by"] in color_options else 0)
        pt_size = st.slider("Point size", 1, 8, int(st.session_state["umap_pt_size"]))
        pt_opacity = st.slider("Opacity", 0.1, 1.0, float(st.session_state["umap_pt_opacity"]), step=0.05)
        apply_view = st.form_submit_button("Apply view", use_container_width=True)
    if apply_view:
        st.session_state["umap_color_by"] = color_by
        st.session_state["umap_pt_size"] = pt_size
        st.session_state["umap_pt_opacity"] = pt_opacity
        st.session_state["umap_apply_nonce"] = st.session_state.get("umap_apply_nonce", 0) + 1

    # Cluster summary
    st.markdown("---")
    st.markdown("#### Cluster sizes")
    cc = adata.obs["leiden"].value_counts().reset_index()
    cc.columns = ["Cluster", "Cells"]
    cc["Pct"] = (cc["Cells"] / adata.n_obs * 100).round(1)
    st.dataframe(cc, use_container_width=True, height=260)

with col_umap:
    fig = umap_plot(adata, color=st.session_state["umap_color_by"],
                    title=f"UMAP — {st.session_state['umap_color_by']}")
    fig.update_traces(marker=dict(size=st.session_state["umap_pt_size"], opacity=st.session_state["umap_pt_opacity"]))
    fig.update_layout(
        paper_bgcolor="#0E1117", plot_bgcolor="#161B22",
        height=560,
        legend=dict(
            bgcolor="rgba(22,27,34,0.8)", bordercolor="#30363D",
            font=dict(size=10), itemsizing="constant"
        )
    )
    st.plotly_chart(fig, use_container_width=True)

# ── PCA variance explained ───────────────────────────────────────────────────
if "pca" in adata.uns and "variance_ratio" in adata.uns["pca"]:
    st.divider()
    st.markdown("### 📉 PCA Variance Explained")
    var_ratio = adata.uns["pca"]["variance_ratio"][:30]
    pca_df = pd.DataFrame({
        "PC": [f"PC{i+1}" for i in range(len(var_ratio))],
        "Variance Ratio (%)": var_ratio * 100,
        "Cumulative (%)": (var_ratio.cumsum()) * 100
    })
    fig_pca = px.bar(pca_df, x="PC", y="Variance Ratio (%)",
                     title="PCA Variance Explained (top 30 PCs)",
                     color="Variance Ratio (%)", color_continuous_scale="Blues",
                     template=PLOTLY_TEMPLATE)
    fig_pca.add_scatter(x=pca_df["PC"], y=pca_df["Cumulative (%)"],
                        mode="lines+markers", name="Cumulative",
                        line=dict(color="#FF6B6B", width=2))
    fig_pca.update_layout(paper_bgcolor="#0E1117", plot_bgcolor="#161B22")
    st.plotly_chart(fig_pca, use_container_width=True)

render_nav_buttons(3)
