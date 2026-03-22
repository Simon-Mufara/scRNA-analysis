import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from utils.annotation import (
    annotate_cells, manual_annotate, score_marker_genes,
    get_cluster_marker_scores, CANONICAL_MARKERS,
    benchmark_annotation_methods, train_reference_classifier, predict_with_reference_classifier
)
from utils.visualization import umap_plot
from utils.styles import inject_global_css, page_header, render_sidebar, render_nav_buttons, show_guidance, PALETTE
from utils.interpretation import show_explanation_button, interpret_cell_types
from config import CELLTYPIST_MODEL
from core.pipeline import get_ranked_genes_df

st.set_page_config(page_title="Cell Type Annotation", layout="wide")
inject_global_css()
render_sidebar()

page_header(
    "🏷️", "Cell Type Annotation",
    "Identify and label cell populations using marker genes, scoring models, or CellTypist AI"
)
show_guidance("annotation")

adata = st.session_state.get("adata")
if adata is None:
    st.warning("⚠️ Please upload a dataset first (Step 1).")
    st.stop()
if "leiden" not in adata.obs.columns:
    st.warning("⚠️ Run clustering (Step 3) before annotation.")
    st.stop()

# ── Method selector ──────────────────────────────────────────────────────────
st.markdown("### Select Annotation Method")
method_cols = st.columns(3)
with method_cols[0]:
    st.markdown("""
    <div style="background:linear-gradient(135deg,rgba(0,212,255,0.08),rgba(0,212,255,0.02));
    border:1px solid rgba(0,212,255,0.3);border-radius:12px;padding:16px;min-height:100px;">
    <b style="color:#00D4FF;">🧬 Marker Gene Scoring</b><br>
    <small style="color:#8B949E;">Score cells against 20+ curated canonical marker sets (Scanpy/Cell Ranger style)</small>
    </div>""", unsafe_allow_html=True)
with method_cols[1]:
    st.markdown("""
    <div style="background:linear-gradient(135deg,rgba(123,47,190,0.08),rgba(123,47,190,0.02));
    border:1px solid rgba(123,47,190,0.3);border-radius:12px;padding:16px;min-height:100px;">
    <b style="color:#A855F7;">🤖 CellTypist AI</b><br>
    <small style="color:#8B949E;">Pre-trained deep learning models for immune, fetal, and pan-tissue cell types</small>
    </div>""", unsafe_allow_html=True)
with method_cols[2]:
    st.markdown("""
    <div style="background:linear-gradient(135deg,rgba(81,207,102,0.08),rgba(81,207,102,0.02));
    border:1px solid rgba(81,207,102,0.3);border-radius:12px;padding:16px;min-height:100px;">
    <b style="color:#51CF66;">✏️ Manual Mapping</b><br>
    <small style="color:#8B949E;">Directly assign cell type labels to each Leiden cluster (Seurat-style)</small>
    </div>""", unsafe_allow_html=True)

st.divider()

tab_marker, tab_celltypist, tab_manual, tab_validation = st.tabs([
    "🧬 Marker Gene Scoring", "🤖 CellTypist AI", "✏️ Manual Mapping", "🧪 Validation & Training"
])

# ──────────────────────────────────────────────────────────────────────────────
# TAB 1 — Marker Gene Scoring
# ──────────────────────────────────────────────────────────────────────────────
with tab_marker:
    st.markdown("""
    **How it works:** Uses `sc.tl.score_genes()` (same engine as Seurat's AddModuleScore)
    to compute a per-cell score for each canonical cell type based on curated marker gene lists.
    The cell type with the highest score is assigned.
    """)

    col_a, col_b = st.columns([2, 1])
    with col_a:
        # Show which marker sets have coverage
        st.markdown("#### Canonical Marker Sets Coverage")
        cov_data = []
        for ct, genes in CANONICAL_MARKERS.items():
            found = [g for g in genes if g in adata.var_names]
            cov_data.append({
                "Cell Type": ct,
                "Total Markers": len(genes),
                "Found in Dataset": len(found),
                "Coverage %": f"{len(found)/len(genes)*100:.0f}%",
                "Status": "✅ Available" if len(found) >= 2 else "⚠️ Insufficient"
            })
        cov_df = pd.DataFrame(cov_data)
        st.dataframe(cov_df, use_container_width=True, height=300)

    with col_b:
        available = sum(1 for d in cov_data if d["Found in Dataset"] >= 2)
        st.metric("Marker Sets Available", f"{available} / {len(CANONICAL_MARKERS)}")
        threshold = st.slider(
            "Min confidence score", 0.0, 2.0, 0.0, 0.1,
            help="Cells below this threshold are labeled 'Unassigned'"
        )
        st.caption("Set to 0.0 to annotate all cells regardless of confidence.")

    if st.button("▶ Run Marker Gene Scoring", type="primary", key="run_marker"):
        with st.spinner("Scoring cells against canonical markers..."):
            try:
                adata = score_marker_genes(adata, score_threshold=threshold)
                st.session_state["adata"] = adata
                st.session_state.setdefault("pipeline_status", {})["Annotation"] = "done"
                n_types = adata.obs["cell_type"].nunique()
                st.success(f"✅ Annotation complete — {n_types} cell types identified")
            except Exception as e:
                st.error(f"Scoring failed: {e}")
                st.info("Tip: ensure normalization/log1p was applied in Step 3.")

    if "marker_scores" in getattr(adata, "uns", {}) and "cell_type_conf" in adata.obs.columns:
        if st.button("🔗 Build Consensus Labels (Marker + CellTypist)", key="run_consensus"):
            with st.spinner("Combining marker and CellTypist annotations..."):
                try:
                    adata = score_marker_genes(
                        adata,
                        score_threshold=threshold,
                        label_col="marker_cell_type",
                        score_col="marker_annotation_score",
                        store_key="marker_scores_consensus",
                    )
                    marker_scores = adata.obs["marker_annotation_score"].astype(float)
                    marker_norm = (marker_scores - marker_scores.min()) / (marker_scores.max() - marker_scores.min() + 1e-9)
                    ct_conf = adata.obs["cell_type_conf"].astype(float).clip(0.0, 1.0)
                    consensus = []
                    consensus_conf = []
                    for idx in adata.obs_names:
                        ct_label = str(adata.obs.at[idx, "cell_type"])
                        mk_label = str(adata.obs.at[idx, "marker_cell_type"])
                        c_conf = float(ct_conf.loc[idx])
                        m_conf = float(marker_norm.loc[idx])
                        if ct_label == mk_label:
                            consensus.append(ct_label)
                            consensus_conf.append(round(max(c_conf, m_conf), 4))
                        elif c_conf >= m_conf + 0.15:
                            consensus.append(ct_label)
                            consensus_conf.append(round(c_conf, 4))
                        elif m_conf >= c_conf + 0.15:
                            consensus.append(mk_label)
                            consensus_conf.append(round(m_conf, 4))
                        else:
                            consensus.append(f"Ambiguous ({ct_label} vs {mk_label})")
                            consensus_conf.append(round(max(c_conf, m_conf), 4))
                    adata.obs["cell_type_consensus"] = pd.Series(consensus, index=adata.obs_names, dtype="string")
                    adata.obs["cell_type_consensus_conf"] = pd.Series(consensus_conf, index=adata.obs_names, dtype="float64")
                    st.session_state["adata"] = adata
                    st.success("✅ Consensus labels created in `cell_type_consensus`.")
                except Exception as e:
                    st.error(f"Consensus labeling failed: {e}")

    # Show heatmap of cluster × cell type scores
    if "marker_scores" in getattr(adata, "uns", {}):
        st.markdown("#### 🔥 Cluster × Cell Type Score Heatmap")
        heat_df = get_cluster_marker_scores(adata)
        if not heat_df.empty:
            fig = go.Figure(go.Heatmap(
                z=heat_df.values,
                x=heat_df.columns.tolist(),
                y=heat_df.index.tolist(),
                colorscale="Plasma",
                colorbar=dict(title="Mean Score"),
            ))
            fig.update_layout(
                template="plotly_dark",
                title="Mean Marker Gene Score per Cluster",
                xaxis_title="Cluster",
                yaxis_title="Cell Type",
                height=max(400, len(heat_df) * 30),
                paper_bgcolor="#0E1117",
                plot_bgcolor="#161B22",
            )
            st.plotly_chart(fig, use_container_width=True)

    if "cell_type_consensus" in adata.obs.columns:
        st.markdown("#### Consensus Label Summary")
        consensus_counts = adata.obs["cell_type_consensus"].value_counts().reset_index()
        consensus_counts.columns = ["Consensus Label", "# Cells"]
        st.dataframe(consensus_counts, use_container_width=True)
        ambiguous_n = int((adata.obs["cell_type_consensus"].astype(str).str.startswith("Ambiguous")).sum())
        st.metric("Ambiguous Cells", f"{ambiguous_n:,}")

# ──────────────────────────────────────────────────────────────────────────────
# TAB 2 — CellTypist AI
# ──────────────────────────────────────────────────────────────────────────────
with tab_celltypist:
    st.markdown("""
    **CellTypist** uses pre-trained logistic regression + deep learning models trained on
    millions of cells across tissues. It's the same approach used in large atlas projects
    (Human Cell Atlas, Tabula Sapiens).
    """)

    # Curated model list — validated against celltypist.models.models_description()
    CELLTYPIST_MODELS = [
        ("Immune_All_Low.pkl",          "Immune cells — 20 tissues, 18 studies (broad, recommended)"),
        ("Immune_All_High.pkl",         "Immune cells — 20 tissues, 18 studies (fine-grained)"),
        ("Healthy_COVID19_PBMC.pkl",    "PBMC — healthy & COVID-19 individuals"),
        ("Adult_COVID19_PBMC.pkl",      "PBMC — COVID-19 patients & controls"),
        ("COVID19_Immune_Landscape.pkl","Immune subtypes — COVID-19 lung & blood"),
        ("Human_Colorectal_Cancer.pkl", "Colorectal cancer — tumour microenvironment"),
        ("Human_Lung_Atlas.pkl",        "Human Lung Cell Atlas — respiratory system"),
        ("Cells_Lung_Airway.pkl",       "Lung & airway — 5 anatomical locations"),
        ("Healthy_Human_Liver.pkl",     "Adult human liver — scRNA + snRNA"),
        ("Pan_Fetal_Human.pkl",         "Human fetus — stromal & immune (pan-tissue)"),
        ("Developing_Human_Thymus.pkl", "Human thymus — embryonic to adult"),
        ("Cells_Human_Tonsil.pkl",      "Human tonsil — 3–65 years"),
        ("Adult_Human_Skin.pkl",        "Adult human skin"),
        ("Cells_Intestinal_Tract.pkl",  "Gut — fetal, pediatric, adult"),
        ("Healthy_Adult_Heart.pkl",     "Heart — 8 anatomical regions"),
    ]

    c1, c2, c3, c4 = st.columns(4)
    model_choice = c1.selectbox(
        "Model",
        options=[m[0] for m in CELLTYPIST_MODELS],
        format_func=lambda x: next((f"{m[0].replace('.pkl','')} — {m[1][:45]}..." for m in CELLTYPIST_MODELS if m[0] == x), x),
        help="Choose a model matching your tissue/cell type. Models are downloaded on first use."
    )
    # Show selected model description
    selected_desc = next((m[1] for m in CELLTYPIST_MODELS if m[0] == model_choice), "")
    c1.caption(f"📋 {selected_desc}")

    majority_voting = c2.checkbox(
        "Majority voting", value=True,
        help="Use cluster-level majority vote for more consistent labels (recommended)"
    )
    min_ct_conf = c3.slider(
        "Minimum CellTypist confidence",
        0.0,
        1.0,
        0.50,
        0.05,
        help="Predictions below this threshold are set to Unassigned.",
    )
    c3.markdown("""
    <br>
    <a href="https://www.celltypist.org/models" target="_blank"
       style="color:#00D4FF;font-size:0.85rem;">📚 Browse all 60+ models →</a>
    """, unsafe_allow_html=True)
    c4.markdown("""
    <br>
    <a href="https://www.celltypist.org/models" target="_blank"
       style="color:#00D4FF;font-size:0.85rem;">🧠 Model docs</a>
    """, unsafe_allow_html=True)

    if st.button("▶ Run CellTypist Annotation", type="primary", key="run_ct"):
        with st.spinner(f"Loading {model_choice} and annotating {adata.n_obs:,} cells..."):
            try:
                adata = annotate_cells(adata, model_name=model_choice,
                                       majority_voting=majority_voting)
                low_conf_mask = adata.obs["cell_type_conf"].astype(float) < float(min_ct_conf)
                adata.obs.loc[low_conf_mask, "cell_type"] = "Unassigned"
                st.session_state["adata"] = adata
                st.session_state.setdefault("pipeline_status", {})["Annotation"] = "done"
                n_types = adata.obs["cell_type"].nunique()
                st.success(f"✅ CellTypist complete — {n_types} cell types predicted")
            except Exception as e:
                st.error(f"CellTypist failed: {e}")
                if "No such file" in str(e) or "not found" in str(e).lower():
                    st.warning("Model not downloaded yet. Make sure you have an internet connection — CellTypist will download it automatically on first use.")
                elif "NaN" in str(e):
                    st.warning("Dataset may have missing values. Try running QC (Step 2) first to filter problem cells.")
                else:
                    st.info("Try the Marker Gene Scoring tab for an offline alternative.")

    if "cell_type_conf" in adata.obs.columns:
        st.markdown("#### Confidence Score Distribution")
        fig = px.histogram(
            adata.obs, x="cell_type_conf", nbins=50,
            title="CellTypist Confidence Scores",
            labels={"cell_type_conf": "Confidence Score"},
            color_discrete_sequence=["#A855F7"],
            template="plotly_dark",
        )
        fig.add_vline(x=0.5, line_dash="dash", line_color="#FF6B6B",
                      annotation_text="0.5 threshold")
        fig.update_layout(paper_bgcolor="#0E1117", plot_bgcolor="#161B22")
        st.plotly_chart(fig, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# TAB 3 — Manual Mapping
# ──────────────────────────────────────────────────────────────────────────────
with tab_manual:
    st.markdown("""
    **Seurat-style manual annotation.** Review marker genes for each cluster
    and assign cell type labels directly.
    """)

    clusters = sorted(adata.obs["leiden"].unique(), key=lambda x: int(x))
    n_clusters = len(clusters)

    # Show top genes per cluster if DE was run
    if "rank_genes_groups" in adata.uns:
        st.markdown("#### Top Markers per Cluster (from Step 6 DE)")
        for cl in clusters[:6]:  # preview first 6
            try:
                top = get_ranked_genes_df(adata, group=str(cl)).head(5)
                top_genes = ", ".join(top["names"].tolist())
                n_cells = (adata.obs["leiden"] == cl).sum()
                st.markdown(
                    f'<span style="color:#00D4FF;font-weight:700;">Cluster {cl}</span> '
                    f'<span style="color:#8B949E;font-size:0.8rem;">({n_cells} cells)</span>  '
                    f'→ <span style="color:#A9E34B;">{top_genes}</span>',
                    unsafe_allow_html=True
                )
            except Exception:
                pass
        st.divider()

    # Cluster label inputs
    st.markdown("#### Assign Cell Type Labels")
    mapping = {}
    cols_per_row = 3
    rows = [clusters[i:i+cols_per_row] for i in range(0, n_clusters, cols_per_row)]

    common_types = list(CANONICAL_MARKERS.keys()) + ["Unknown", "Other"]

    for row in rows:
        row_cols = st.columns(cols_per_row)
        for i, cluster in enumerate(row):
            n_cells = int((adata.obs["leiden"] == cluster).sum())
            existing = adata.obs.get("cell_type", pd.Series())
            # Pre-fill if already annotated
            default_idx = 0
            if "cell_type" in adata.obs.columns:
                # most common cell type in this cluster
                try:
                    cluster_mask = adata.obs["leiden"] == cluster
                    top_ct = adata.obs.loc[cluster_mask, "cell_type"].mode()[0]
                    if top_ct in common_types:
                        default_idx = common_types.index(top_ct)
                except Exception:
                    pass
            with row_cols[i]:
                selected = st.selectbox(
                    f"Cluster {cluster} ({n_cells:,} cells)",
                    options=common_types,
                    index=default_idx,
                    key=f"manual_ct_{cluster}"
                )
                mapping[cluster] = selected

    if st.button("✅ Apply Manual Annotation", type="primary", key="apply_manual"):
        adata = manual_annotate(adata, cluster_map=mapping)
        st.session_state["adata"] = adata
        st.session_state.setdefault("pipeline_status", {})["Annotation"] = "done"
        st.success("✅ Manual annotation applied!")

# ──────────────────────────────────────────────────────────────────────────────
# TAB 4 — Validation & Training
# ──────────────────────────────────────────────────────────────────────────────
with tab_validation:
    st.markdown("Use labeled references to benchmark methods and train a custom classifier for your context.")
    label_candidates = [c for c in adata.obs.columns if adata.obs[c].dtype == "object" or str(adata.obs[c].dtype).startswith("string")]
    if not label_candidates:
        st.info("No label-like columns found yet. Create or import labels first.")
    else:
        truth_col = st.selectbox("Ground truth / reference label column", options=label_candidates)
        pred_candidates = [c for c in ["cell_type", "cell_type_consensus", "marker_cell_type", "cell_type_custom"] if c in adata.obs.columns]
        if pred_candidates:
            if st.button("📊 Benchmark current annotation methods", key="benchmark_methods"):
                try:
                    bench_df = benchmark_annotation_methods(adata, truth_col=truth_col, pred_cols=pred_candidates)
                    if bench_df.empty:
                        st.warning("No comparable prediction columns available for benchmarking.")
                    else:
                        st.dataframe(bench_df, use_container_width=True)
                        st.session_state["annotation_benchmark_df"] = bench_df
                except Exception as e:
                    st.error(f"Benchmarking failed: {e}")
        else:
            st.caption("Run at least one annotation method first to benchmark.")

        st.markdown("#### Train custom reference classifier")
        cta1, cta2, cta3 = st.columns(3)
        n_pcs = cta1.slider("Number of PCs", 10, 80, 30, 5)
        test_fraction = cta2.slider("Validation split", 0.1, 0.4, 0.2, 0.05)
        conf_threshold = cta3.slider("Minimum custom confidence", 0.0, 1.0, 0.5, 0.05)
        if st.button("🧠 Train + Apply custom classifier", type="primary", key="train_custom_clf"):
            with st.spinner("Training custom classifier and applying predictions..."):
                try:
                    clf, metrics = train_reference_classifier(
                        adata,
                        label_col=truth_col,
                        n_pcs=n_pcs,
                        test_fraction=test_fraction,
                    )
                    adata = predict_with_reference_classifier(
                        adata,
                        classifier=clf,
                        n_pcs=n_pcs,
                        label_col="cell_type_custom",
                        conf_col="cell_type_custom_conf",
                    )
                    low_conf = adata.obs["cell_type_custom_conf"].astype(float) < float(conf_threshold)
                    adata.obs.loc[low_conf, "cell_type_custom"] = "Unassigned"
                    st.session_state["adata"] = adata
                    st.session_state["annotation_custom_metrics"] = metrics
                    st.success(
                        "✅ Custom classifier ready "
                        f"(accuracy={metrics['accuracy']:.3f}, macro_f1={metrics['macro_f1']:.3f}, classes={metrics['n_classes']})."
                    )
                except Exception as e:
                    st.error(f"Custom training failed: {e}")

        metrics = st.session_state.get("annotation_custom_metrics")
        if metrics:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Custom Accuracy", f"{metrics.get('accuracy', 0):.3f}")
            m2.metric("Custom Macro F1", f"{metrics.get('macro_f1', 0):.3f}")
            m3.metric("Train Cells", f"{metrics.get('n_train', 0):,}")
            m4.metric("Validation Cells", f"{metrics.get('n_test', 0):,}")

# ── Results visualisation ────────────────────────────────────────────────────
if "cell_type" in adata.obs.columns:
    st.divider()
    st.markdown("## 📊 Annotation Results")

    counts = adata.obs["cell_type"].value_counts().reset_index()
    counts.columns = ["Cell Type", "# Cells"]
    counts["Proportion (%)"] = (counts["# Cells"] / adata.n_obs * 100).round(2)

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Cells", f"{adata.n_obs:,}")
    m2.metric("Cell Types Found", counts.shape[0])
    m3.metric("Most Abundant", counts.iloc[0]["Cell Type"])

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        fig = px.bar(
            counts, x="# Cells", y="Cell Type", orientation="h",
            color="# Cells", color_continuous_scale="Viridis",
            title="Cell Type Abundance",
            template="plotly_dark",
        )
        fig.update_layout(
            yaxis={"categoryorder": "total ascending"},
            paper_bgcolor="#0E1117", plot_bgcolor="#161B22",
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_chart2:
        fig = px.pie(
            counts, names="Cell Type", values="# Cells",
            title="Cell Type Proportions",
            color_discrete_sequence=PALETTE,
            template="plotly_dark",
            hole=0.4,
        )
        fig.update_layout(paper_bgcolor="#0E1117")
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    if "X_umap" in adata.obsm:
        st.markdown("#### UMAP — Cell Types")
        fig = umap_plot(adata, color="cell_type", title="UMAP — Cell Types")
        fig.update_traces(marker=dict(size=3, opacity=0.8))
        fig.update_layout(paper_bgcolor="#0E1117", plot_bgcolor="#161B22")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Cell Type Table")
    st.dataframe(counts, use_container_width=True)

    st.markdown("#### Tooling Options (for broader workflows)")
    st.markdown(
        """
- **Annotation alternatives:** SingleR, scANVI/scVI-tools, Azimuth/Seurat reference mapping, scmap.
- **Doublet detection:** Scrublet, DoubletFinder.
- **Batch integration options:** Harmony, BBKNN, Scanorama, Seurat integration.
- **Pathway alternatives:** fgsea, clusterProfiler, decoupler.
Use alternatives for cross-validation when results are clinically sensitive.
"""
    )

    csv = counts.to_csv(index=False).encode()
    st.download_button("⬇️ Download Cell Type Summary (CSV)", data=csv,
                       file_name="cell_type_summary.csv", mime="text/csv")

# ── Explanations ───────────────────────────────────────────────────────────────
st.divider()
st.markdown("### 💡 Understanding Cell Type Annotations")
with st.expander("📖 What do these results mean?", expanded=False):
    cell_type_interpretations = interpret_cell_types(adata, "cell_type")
    for cell_type, interpretation in cell_type_interpretations.items():
        st.markdown(f"- {interpretation}")

    st.markdown("\n**Validation Tips:**")
    st.markdown("""
    - ✅ Compare against known biology (prior knowledge)
    - ✅ Check marker gene expression in annotation results
    - ✅ Look for biologically consistent cluster composition
    - ⚠️ Ambiguous cells may represent transitional states
    """)

show_explanation_button("celltype", adata, button_key="celltype_explain")

render_nav_buttons(5)
