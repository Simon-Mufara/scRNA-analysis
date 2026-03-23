import streamlit as st
from config import APP_TITLE, APP_ICON, PIPELINE_STEPS
from utils.styles import inject_global_css, render_sidebar, render_nav_buttons, PALETTE

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()
render_sidebar()

# ── Hero ──────────────────────────────────────────────────────────────────────
hero_col, img_col = st.columns([3, 2])
with hero_col:
    st.markdown(f"""
    <div style="padding:12px 0 24px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
            <span style="background:rgba(81,207,102,0.15);color:#51CF66;
                border:1px solid rgba(81,207,102,0.3);border-radius:20px;
                padding:3px 12px;font-size:0.72rem;font-weight:600;letter-spacing:0.04em;">
                ● LIVE PLATFORM
            </span>
            <span style="color:#6E7681;font-size:0.72rem;">v1.0.0</span>
        </div>
        <h1 style="font-size:2.5rem !important;line-height:1.15;margin:0 0 12px;">
            Single-Cell RNA-seq<br>Clinical Explorer
        </h1>
        <p style="color:#8B949E;font-size:1rem;line-height:1.7;margin:0 0 20px;max-width:520px;">
            End-to-end scRNA-seq analysis — from raw counts to clinical insights.
            Built for researchers, clinicians, and biotech teams working with
            immune, cancer, and developmental datasets.
        </p>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
            <span style="background:rgba(0,212,255,0.1);color:#00D4FF;border:1px solid rgba(0,212,255,0.3);border-radius:20px;padding:4px 14px;font-size:0.78rem;font-weight:600;">🔬 Researchers</span>
            <span style="background:rgba(168,85,247,0.1);color:#A855F7;border:1px solid rgba(168,85,247,0.3);border-radius:20px;padding:4px 14px;font-size:0.78rem;font-weight:600;">🏥 Clinicians</span>
            <span style="background:rgba(81,207,102,0.1);color:#51CF66;border:1px solid rgba(81,207,102,0.3);border-radius:20px;padding:4px 14px;font-size:0.78rem;font-weight:600;">🏭 Biotech</span>
            <span style="background:rgba(255,107,107,0.1);color:#FF6B6B;border:1px solid rgba(255,107,107,0.3);border-radius:20px;padding:4px 14px;font-size:0.78rem;font-weight:600;">📦 100 GB+</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    cta_a, cta_b = st.columns([1, 1])
    with cta_a:
        if st.button("🚀  Start Analysis →", type="primary", key="hero_cta"):
            st.switch_page("pages/1_Upload_Data.py")
    with cta_b:
        if st.button("📘  Open User Guide", key="hero_guide"):
            st.switch_page("pages/0_User_Guide.py")

with img_col:
    # Free microscopy image — Unsplash (public domain license)
    st.markdown("""
    <div style="border-radius:20px;overflow:hidden;border:1px solid #21262D;
        height:260px;position:relative;">
        <img src="https://images.unsplash.com/photo-1576086213369-97a306d36557?w=700&q=80"
            style="width:100%;height:100%;object-fit:cover;opacity:0.85;" alt="cells under microscope"/>
        <div style="position:absolute;inset:0;
            background:linear-gradient(135deg,rgba(7,11,20,0.3) 0%,rgba(0,212,255,0.05) 100%);
            border-radius:20px;"></div>
        <div style="position:absolute;bottom:14px;left:14px;">
            <span style="background:rgba(7,11,20,0.75);backdrop-filter:blur(6px);
                color:#8B949E;font-size:0.7rem;padding:4px 10px;border-radius:20px;
                border:1px solid #21262D;">
                📸 Immune cells · fluorescence microscopy
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Platform stats bar ────────────────────────────────────────────────────────
stats = st.columns(5)
stat_items = [
    ("8", "Pipeline Steps",   "#00D4FF"),
    ("100 GB+", "Max File Size",    "#A855F7"),
    ("4+", "Pathway Databases", "#51CF66"),
    ("AI", "Cell Annotation",  "#FFD43B"),
    ("PDF", "Clinical Reports", "#FF6B6B"),
]
for col, (val, label, color) in zip(stats, stat_items):
    with col:
        st.markdown(f"""
        <div style="
            background:rgba(22,27,34,0.6);
            backdrop-filter:blur(10px);
            border:1px solid #21262D;
            border-top:2px solid {color};
            border-radius:12px;padding:16px 14px;text-align:center;
            transition:all 0.2s;
        ">
            <div style="color:{color};font-size:1.6rem;font-weight:800;
                        letter-spacing:-0.04em;line-height:1;">{val}</div>
            <div style="color:#6E7681;font-size:0.72rem;text-transform:uppercase;
                        letter-spacing:0.08em;margin-top:5px;font-weight:500;">{label}</div>
        </div>
        """, unsafe_allow_html=True)

# ── Pipeline tracker ──────────────────────────────────────────────────────────
st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
st.markdown("""
<div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;">
    <span style="color:#E6EDF3;font-weight:700;font-size:1rem;letter-spacing:-0.02em;">
        Analysis Pipeline
    </span>
    <span style="background:rgba(0,212,255,0.08);color:#6E7681;border:1px solid #21262D;
        border-radius:20px;padding:2px 8px;font-size:0.7rem;">8 steps</span>
</div>
""", unsafe_allow_html=True)

completed = st.session_state.get("pipeline_status", {})
steps = list(PIPELINE_STEPS.items())

pipeline_html = '<div style="display:flex;gap:0;align-items:center;overflow-x:auto;padding:4px 0 8px;">'
for i, (step, icon) in enumerate(steps):
    status = completed.get(step, "pending")
    if status == "done":
        bg      = "rgba(81,207,102,0.12)"
        border  = "rgba(81,207,102,0.45)"
        num_bg  = "#51CF66"
        t_color = "#51CF66"
        num_txt = "✓"
        num_col = "#0D1117"
    else:
        bg      = "rgba(22,27,34,0.7)"
        border  = "#21262D"
        num_bg  = "#21262D"
        t_color = "#6E7681"
        num_txt = str(i + 1)
        num_col = "#8B949E"

    pipeline_html += f"""
    <div style="
        background:{bg};border:1px solid {border};border-radius:12px;
        padding:12px 16px;min-width:115px;text-align:center;flex-shrink:0;
        backdrop-filter:blur(8px);transition:all 0.2s;
    ">
        <div style="font-size:1.4rem;line-height:1;">{icon}</div>
        <div style="color:{t_color};font-size:0.7rem;font-weight:700;
                    text-transform:uppercase;letter-spacing:0.07em;margin-top:5px;">{step}</div>
        <div style="
            display:inline-flex;align-items:center;justify-content:center;
            width:18px;height:18px;background:{num_bg};
            border-radius:50%;font-size:0.62rem;font-weight:700;
            color:{num_col};margin-top:5px;
        ">{num_txt}</div>
    </div>"""
    if i < len(steps) - 1:
        arrow_color = "#30363D" if status != "done" else "rgba(81,207,102,0.5)"
        pipeline_html += f'<div style="color:{arrow_color};font-size:1rem;padding:0 3px;flex-shrink:0;">›</div>'

pipeline_html += "</div>"
st.markdown(pipeline_html, unsafe_allow_html=True)

# ── Full Workflow Pipeline Diagram ─────────────────────────────────────────────
with st.expander("📊 Full Workflow Pipeline", expanded=False):
    st.markdown("""
    <div style="background:rgba(22,27,34,0.4);border:1px solid #21262D;border-radius:14px;padding:20px;">
        <div style="font-size:0.85rem;color:#8B949E;line-height:1.8;">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                <span style="background:#00D4FF;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#0E1117;font-weight:700;font-size:0.7rem;">1</span>
                <div>
                    <div style="color:#E6EDF3;font-weight:600;font-size:0.9rem;">📁 Upload Data</div>
                    <div style="color:#6E7681;font-size:0.75rem;margin-top:2px;">Load .h5ad file or matrix data</div>
                </div>
            </div>

            <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                <span style="background:#A855F7;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#0E1117;font-weight:700;font-size:0.7rem;">2</span>
                <div>
                    <div style="color:#E6EDF3;font-weight:600;font-size:0.9rem;">🔬 Quality Control</div>
                    <div style="color:#6E7681;font-size:0.75rem;margin-top:2px;">Filter low-quality cells and genes</div>
                </div>
            </div>

            <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                <span style="background:#51CF66;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#0E1117;font-weight:700;font-size:0.7rem;">3</span>
                <div>
                    <div style="color:#E6EDF3;font-weight:600;font-size:0.9rem;">📊 Clustering & UMAP</div>
                    <div style="color:#6E7681;font-size:0.75rem;margin-top:2px;">Normalize, reduce dimensions, identify clusters</div>
                </div>
            </div>

            <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                <span style="background:#FF6B6B;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#0E1117;font-weight:700;font-size:0.7rem;">4</span>
                <div>
                    <div style="color:#E6EDF3;font-weight:600;font-size:0.9rem;">🏷️ Cell Type Annotation</div>
                    <div style="color:#6E7681;font-size:0.75rem;margin-top:2px;">Assign cell types using markers or AI</div>
                </div>
            </div>

            <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                <span style="background:#FFD43B;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#0E1117;font-weight:700;font-size:0.7rem;">5</span>
                <div>
                    <div style="color:#E6EDF3;font-weight:600;font-size:0.9rem;">🔎 Gene Explorer</div>
                    <div style="color:#6E7681;font-size:0.75rem;margin-top:2px;">Visualize expression of specific genes</div>
                </div>
            </div>

            <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                <span style="background:#FF922B;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#0E1117;font-weight:700;font-size:0.7rem;">6</span>
                <div>
                    <div style="color:#E6EDF3;font-weight:600;font-size:0.9rem;">📈 Differential Expression</div>
                    <div style="color:#6E7681;font-size:0.75rem;margin-top:2px;">Find genes distinguishing cell types</div>
                </div>
            </div>

            <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                <span style="background:#74C0FC;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#0E1117;font-weight:700;font-size:0.7rem;">7</span>
                <div>
                    <div style="color:#E6EDF3;font-weight:600;font-size:0.9rem;">🧪 Pathway Analysis</div>
                    <div style="color:#6E7681;font-size:0.75rem;margin-top:2px;">Identify enriched biological pathways</div>
                </div>
            </div>

            <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                <span style="background:#63E6BE;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#0E1117;font-weight:700;font-size:0.7rem;">8</span>
                <div>
                    <div style="color:#E6EDF3;font-weight:600;font-size:0.9rem;">📋 Summary Report</div>
                    <div style="color:#6E7681;font-size:0.75rem;margin-top:2px;">Aggregate all results and insights</div>
                </div>
            </div>

            <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                <span style="background:#9775FA;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#0E1117;font-weight:700;font-size:0.7rem;">9</span>
                <div>
                    <div style="color:#E6EDF3;font-weight:600;font-size:0.9rem;">📄 Clinical Report</div>
                    <div style="color:#6E7681;font-size:0.75rem;margin-top:2px;">Export publication-ready PDF report</div>
                </div>
            </div>

            <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                <span style="background:#20C997;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#0E1117;font-weight:700;font-size:0.7rem;">10</span>
                <div>
                    <div style="color:#E6EDF3;font-weight:600;font-size:0.9rem;">👥 Team Dashboard</div>
                    <div style="color:#6E7681;font-size:0.75rem;margin-top:2px;">Share results and collaborate with team</div>
                </div>
            </div>

            <div style="display:flex;align-items:center;gap:12px;">
                <span style="background:#868E96;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#0E1117;font-weight:700;font-size:0.7rem;">11</span>
                <div>
                    <div style="color:#E6EDF3;font-weight:600;font-size:0.9rem;">⚙️ Preprocessing Workbench</div>
                    <div style="color:#6E7681;font-size:0.75rem;margin-top:2px;">Data import and preprocessing utilities</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Dataset status ────────────────────────────────────────────────────────────
adata = st.session_state.get("adata")
st.markdown("<div style='margin-top:4px;'></div>", unsafe_allow_html=True)
st.divider()

if adata is not None:
    import plotly.express as px

    col_info, col_charts = st.columns([1, 2])
    with col_info:
        st.markdown("""
        <div style="
            background:rgba(81,207,102,0.07);
            border:1px solid rgba(81,207,102,0.3);
            border-radius:14px;padding:16px 20px;margin-bottom:16px;
            display:flex;align-items:center;gap:10px;
        ">
            <span style="font-size:1.4rem;">✅</span>
            <div>
                <div style="color:#51CF66;font-weight:700;font-size:0.9rem;">Dataset Loaded</div>
                <div style="color:#6E7681;font-size:0.78rem;margin-top:2px;">Ready for analysis</div>
            </div>
        </div>""", unsafe_allow_html=True)

        m1, m2 = st.columns(2)
        m1.metric("Cells", f"{adata.n_obs:,}")
        m2.metric("Genes", f"{adata.n_vars:,}")
        if "leiden" in adata.obs.columns:
            m1.metric("Clusters", adata.obs["leiden"].nunique())
        if "cell_type" in adata.obs.columns:
            m2.metric("Cell Types", adata.obs["cell_type"].nunique())

    with col_charts:
        if "cell_type" in adata.obs.columns:
            ct_counts = adata.obs["cell_type"].value_counts().reset_index()
            ct_counts.columns = ["Cell Type", "Cells"]
            fig = px.pie(ct_counts, names="Cell Type", values="Cells",
                         color_discrete_sequence=PALETTE,
                         hole=0.48, template="plotly_dark",
                         title="Cell Type Composition")
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                height=300, showlegend=True,
                legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
                title_font=dict(size=13, color="#8B949E"),
                margin=dict(t=36, b=8, l=8, r=8)
            )
            fig.update_traces(textposition="inside", textinfo="percent",
                              textfont_size=11)
            st.plotly_chart(fig, width="stretch")
        elif "leiden" in adata.obs.columns:
            cl_counts = adata.obs["leiden"].value_counts().reset_index()
            cl_counts.columns = ["Cluster", "Cells"]
            fig = px.bar(cl_counts, x="Cluster", y="Cells",
                         color="Cells", color_continuous_scale=["#00D4FF", "#7B2FBE"],
                         template="plotly_dark", title="Cluster Sizes")
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                height=300, title_font=dict(size=13, color="#8B949E"),
                margin=dict(t=36, b=8, l=8, r=8)
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("Run clustering (Step 3) to see composition charts.")
else:
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.markdown("""
        <div style="
            background:rgba(13,17,23,0.6);
            border:1px dashed rgba(0,212,255,0.2);
            border-radius:16px;padding:36px 28px;text-align:center;
        ">
            <div style="font-size:2.8rem;margin-bottom:14px;opacity:0.7;">📂</div>
            <div style="color:#C9D1D9;font-size:1.05rem;font-weight:700;
                        letter-spacing:-0.02em;">No dataset loaded</div>
            <div style="color:#6E7681;margin-top:8px;font-size:0.875rem;line-height:1.6;">
                Upload a <code style="color:#00D4FF;background:rgba(0,212,255,0.08);
                padding:1px 5px;border-radius:4px;">.h5ad</code> file to get started.<br>
                Supports files up to <strong style="color:#C9D1D9;">100 GB</strong>.
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_r:
        st.markdown("""
        <div style="
            background:rgba(13,17,23,0.6);
            border:1px solid #21262D;border-radius:16px;padding:28px;
        ">
            <div style="color:#8B949E;font-size:0.72rem;text-transform:uppercase;
                        letter-spacing:0.1em;font-weight:600;margin-bottom:16px;">
                Quick Start Guide
            </div>
            <div style="display:flex;flex-direction:column;gap:12px;">
                <div style="display:flex;gap:12px;align-items:flex-start;">
                    <div style="background:rgba(0,212,255,0.12);color:#00D4FF;
                        border-radius:8px;width:28px;height:28px;display:flex;
                        align-items:center;justify-content:center;font-size:0.75rem;
                        font-weight:700;flex-shrink:0;">1</div>
                    <div>
                        <div style="color:#C9D1D9;font-size:0.875rem;font-weight:600;">Upload Data</div>
                        <div style="color:#6E7681;font-size:0.78rem;margin-top:2px;">
                            Drag &amp; drop your .h5ad file or provide a server path
                        </div>
                    </div>
                </div>
                <div style="display:flex;gap:12px;align-items:flex-start;">
                    <div style="background:rgba(168,85,247,0.12);color:#A855F7;
                        border-radius:8px;width:28px;height:28px;display:flex;
                        align-items:center;justify-content:center;font-size:0.75rem;
                        font-weight:700;flex-shrink:0;">2</div>
                    <div>
                        <div style="color:#C9D1D9;font-size:0.875rem;font-weight:600;">Quality Control</div>
                        <div style="color:#6E7681;font-size:0.78rem;margin-top:2px;">
                            Filter cells by gene count, mitochondrial %, and more
                        </div>
                    </div>
                </div>
                <div style="display:flex;gap:12px;align-items:flex-start;">
                    <div style="background:rgba(81,207,102,0.12);color:#51CF66;
                        border-radius:8px;width:28px;height:28px;display:flex;
                        align-items:center;justify-content:center;font-size:0.75rem;
                        font-weight:700;flex-shrink:0;">3</div>
                    <div>
                        <div style="color:#C9D1D9;font-size:0.875rem;font-weight:600;">Cluster &amp; Annotate</div>
                        <div style="color:#6E7681;font-size:0.78rem;margin-top:2px;">
                            UMAP visualization + AI-powered cell type assignment
                        </div>
                    </div>
                </div>
                <div style="display:flex;gap:12px;align-items:flex-start;">
                    <div style="background:rgba(255,212,59,0.12);color:#FFD43B;
                        border-radius:8px;width:28px;height:28px;display:flex;
                        align-items:center;justify-content:center;font-size:0.75rem;
                        font-weight:700;flex-shrink:0;">4</div>
                    <div>
                        <div style="color:#C9D1D9;font-size:0.875rem;font-weight:600;">Export &amp; Report</div>
                        <div style="color:#6E7681;font-size:0.78rem;margin-top:2px;">
                            Generate clinical PDF reports and CSV exports
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── Platform capabilities ─────────────────────────────────────────────────────
st.divider()
st.markdown("""
<div style="display:flex;align-items:baseline;gap:10px;margin-bottom:18px;">
    <span style="color:#E6EDF3;font-weight:700;font-size:1rem;letter-spacing:-0.02em;">
        Platform Capabilities
    </span>
    <span style="color:#6E7681;font-size:0.8rem;">8 integrated modules</span>
</div>
""", unsafe_allow_html=True)

features = [
    ("🔬", "QC & Filtering",       "Interactive thresholds with live histograms and violin plots",    "#00D4FF"),
    ("📊", "UMAP Clustering",      "Leiden clustering with interactive Plotly UMAP explorer",         "#A855F7"),
    ("🏷️", "Auto-Annotation",      "Marker scoring + CellTypist AI + manual Seurat-style mapping",   "#51CF66"),
    ("🌋", "Volcano Plots",        "Wilcoxon DE analysis with labeled volcano plots",                 "#FF6B6B"),
    ("🧪", "Pathway Enrichment",   "Enrichr integration: KEGG, Reactome, GO, Hallmark",              "#FFD43B"),
    ("📕", "Clinical PDF Reports", "Styled reports with cell counts, markers, and pathways",          "#FF922B"),
    ("📦", "100 GB+ Support",      "Optimised for very large .h5ad files on Linux servers",           "#74C0FC"),
    ("💾", "CSV Exports",          "Clean, labelled exports at every step of the pipeline",           "#63E6BE"),
]

feat_cols = st.columns(4)
for i, (icon, title, desc, accent) in enumerate(features):
    with feat_cols[i % 4]:
        st.markdown(f"""
        <div style="
            background:rgba(22,27,34,0.55);
            backdrop-filter:blur(8px);
            border:1px solid #21262D;
            border-radius:14px;padding:18px 16px;
            margin-bottom:12px;min-height:120px;
            transition:all 0.2s;
            position:relative;overflow:hidden;
        "
        onmouseover="this.style.borderColor='{accent}40';this.style.background='rgba(22,27,34,0.85)';this.style.transform='translateY(-2px)'"
        onmouseout="this.style.borderColor='#21262D';this.style.background='rgba(22,27,34,0.55)';this.style.transform='translateY(0)'">
            <div style="
                position:absolute;top:0;left:0;right:0;height:2px;
                background:linear-gradient(90deg,{accent},transparent);
                border-radius:14px 14px 0 0;
            "></div>
            <div style="font-size:1.5rem;margin-bottom:8px;line-height:1;">{icon}</div>
            <div style="color:#C9D1D9;font-weight:700;font-size:0.875rem;
                        letter-spacing:-0.01em;">{title}</div>
            <div style="color:#6E7681;font-size:0.78rem;margin-top:5px;
                        line-height:1.5;">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
render_nav_buttons(0)
st.markdown("""
<div style="
    margin-top:32px;
    padding:20px 0 8px;
    border-top:1px solid #161B22;
    display:flex;align-items:center;justify-content:space-between;
    flex-wrap:wrap;gap:8px;
">
    <div style="display:flex;align-items:center;gap:8px;">
        <span style="font-size:1rem;">🧬</span>
        <span style="color:#6E7681;font-size:0.78rem;letter-spacing:-0.01em;">
            SingleCell Clinical &amp; Research Explorer
        </span>
        <span style="background:#21262D;color:#6E7681;border-radius:20px;
            padding:1px 8px;font-size:0.68rem;">v1.0.0</span>
    </div>
    <div style="color:#30363D;font-size:0.75rem;">
        Built with Streamlit · Scanpy · CellTypist · Enrichr
    </div>
</div>
""", unsafe_allow_html=True)
