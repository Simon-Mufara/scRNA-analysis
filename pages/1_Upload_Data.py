import streamlit as st
import pandas as pd
import os
import shutil
import tempfile

from core.preprocessing import load_h5ad_safe as _load_h5ad_safe
from core.preprocessing import load_input_dataset, load_demo_dataset
from core.pipeline import load_dataset_by_format
from utils.styles import inject_global_css, page_header, render_sidebar, render_nav_buttons
from utils.auth import get_current_user


def _safe_unlink(path: str):
    try:
        if path and os.path.exists(path):
            os.unlink(path)
    except OSError:
        pass


def _ensure_disk_space(required_bytes: int, dest_dir: str, overhead_ratio: float = 1.15):
    """Raise a clear error when temp disk space is insufficient for large uploads."""
    free_bytes = shutil.disk_usage(dest_dir).free
    required_with_overhead = int(required_bytes * overhead_ratio)
    if free_bytes < required_with_overhead:
        req_gb = required_with_overhead / (1024 ** 3)
        free_gb = free_bytes / (1024 ** 3)
        raise OSError(
            f"Not enough free disk space in {dest_dir}. "
            f"Need about {req_gb:.2f} GB, available {free_gb:.2f} GB."
        )

st.set_page_config(page_title="Upload Data", layout="wide")
inject_global_css()
render_sidebar()
current_user = get_current_user()
is_demo_user = bool(current_user.get("is_demo"))

# ── Visual banner ──────────────────────────────────────────────────────────────
banner_col, img_col = st.columns([2, 1])
with banner_col:
    page_header(
        "📂", "Upload scRNA-seq Dataset",
        "Load .h5ad, .loom or provide a local file path — supports up to 100 GB"
    )
with img_col:
    st.markdown("""
    <div style="border-radius:14px;overflow:hidden;border:1px solid #21262D;height:100px;margin-top:4px;">
        <img src="https://images.unsplash.com/photo-1530026405186-ed1f139313f8?w=500&q=80"
            style="width:100%;height:100%;object-fit:cover;opacity:0.7;" alt="DNA strand"/>
    </div>
    """, unsafe_allow_html=True)

tab_upload, tab_path, tab_example = st.tabs([
    "📤 Browser Upload (≤100 GB)", "📁 Server File Path (Linux only)", "🧪 Demo Dataset"
])

# ──────────────────────────────────────────────────────────────────────────────
with tab_upload:
    if is_demo_user:
        st.warning("Demo profile: custom file upload is disabled. Create an account to upload your own datasets.")
    st.markdown("""
    <div style="background:linear-gradient(135deg,rgba(0,212,255,0.05),rgba(0,212,255,0.01));
    border:1px dashed rgba(0,212,255,0.4);border-radius:14px;padding:20px;margin-bottom:16px;">
        <b style="color:#00D4FF;">Supported:</b> <code>.h5ad</code> (AnnData) — compatible with Scanpy,
        Cell Ranger, Seurat (via SeuratDisk), CellxGene.<br>
        <span style="color:#8B949E;font-size:0.88rem;">
        Max upload: <b>100 GB</b> (configured in .streamlit/config.toml).
        For files >2 GB on slow connections, use the <b>Server File Path</b> tab — but only if the file is already on the Linux server.
        </span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:rgba(255,107,107,0.08);border:1px solid rgba(255,107,107,0.4);
    border-radius:10px;padding:12px 16px;margin-bottom:12px;">
    <b style="color:#FF6B6B;">⚠️ 400 Error?</b>
    <span style="color:#C9D1D9;font-size:0.9rem;">
    This means the app is still running with an old file size limit.
    Restart the app service so the 100 GB upload limit is applied.
    </span>
    </div>
    """, unsafe_allow_html=True)

    file = st.file_uploader(
        "Drag & drop or browse for your .h5ad file",
        type=["h5ad", "loom"],
        help="Max 100 GB. Large files may take a while to upload — keep this tab open.",
        disabled=is_demo_user,
    )

    if file:
        if not file.name.lower().endswith((".h5ad", ".loom")):
            st.error("Unsupported file extension. Please upload a .h5ad or .loom file.")
            st.stop()

        file_size_mb = file.size / (1024 ** 2)
        st.info(f"📦 File: **{file.name}** ({file_size_mb:,.1f} MB) — processing...")
        tmp_path = None
        with st.spinner("Loading dataset into memory..."):
            try:
                suffix = ".loom" if file.name.lower().endswith(".loom") else ".h5ad"
                if file_size_mb <= 512:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=tempfile.gettempdir()) as tmp:
                        tmp.write(file.getbuffer())
                        tmp_path = tmp.name
                    adata = load_dataset_by_format(tmp_path, suffix)
                else:
                    temp_dir = tempfile.gettempdir()
                    _ensure_disk_space(file.size, temp_dir)

                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=temp_dir) as tmp:
                        # Stream in larger chunks to reduce write overhead for very large uploads.
                        chunk_size = 128 * 1024 * 1024  # 128 MB
                        file.seek(0)
                        while True:
                            chunk = file.read(chunk_size)
                            if not chunk:
                                break
                            tmp.write(chunk)
                        tmp_path = tmp.name

                    adata = load_dataset_by_format(tmp_path, suffix)
            except MemoryError:
                st.error(
                    "The dataset is too large to load fully into memory in this environment. "
                    "Try a machine with more RAM, or reduce/filter the dataset before loading."
                )
                st.stop()
            except OSError as e:
                st.error(f"Storage error while handling upload: {e}")
                st.stop()
            except Exception as e:
                st.error(f"Failed to read uploaded file: {e}")
                st.stop()
            finally:
                _safe_unlink(tmp_path)

        st.session_state["adata"] = adata
        st.session_state.setdefault("pipeline_status", {})["Upload"] = "done"
        st.success(f"✅ **{file.name}** loaded — {adata.n_obs:,} cells × {adata.n_vars:,} genes")

# ──────────────────────────────────────────────────────────────────────────────
with tab_path:
    if is_demo_user:
        st.warning("Demo profile: server-path loading is disabled. Create an account to use your own files.")
    st.markdown("""
    <div style="background:rgba(255,183,77,0.08);border:1px solid rgba(255,183,77,0.4);
    border-radius:10px;padding:14px 18px;margin-bottom:12px;">
    <b style="color:#FFB74D;">⚠️ This tab is for server-side files only</b><br>
    <span style="color:#C9D1D9;font-size:0.9rem;">
    Enter a path that exists <b>on the Linux server</b> (e.g. <code>/data/file.h5ad</code>).<br>
    <b>If your file is on your Windows/Mac laptop</b> → use the <b>Browser Upload</b> tab instead
    (restart Streamlit first to enable 100 GB uploads).
    </span>
    </div>
    """, unsafe_allow_html=True)

    file_path = st.text_input(
        "Absolute server path (Linux)",
        placeholder="/data/human_immune_health_atlas.h5ad"
    )

    col_fmt, col_btn = st.columns([2, 1])
    fmt = col_fmt.selectbox("Format", [".h5ad (AnnData)", ".loom", ".csv (cell×gene)", ".mtx (10x)"])

    if col_btn.button("▶ Load from Path", type="primary", key="load_path", disabled=is_demo_user):
        if not file_path:
            st.warning("Enter a file path.")
        elif not os.path.isabs(file_path):
            st.error("Please provide an absolute Linux path (for example: /users/simon/data/sample.h5ad).")
        elif not os.path.exists(file_path):
            st.error(f"File not found: `{file_path}`")
        else:
            size_gb = os.path.getsize(file_path) / (1024 ** 3)
            with st.spinner(f"Reading {size_gb:.2f} GB file..."):
                try:
                    if ".loom" in fmt:
                        adata = load_input_dataset(file_path, ".loom")
                    elif ".csv" in fmt:
                        adata = load_input_dataset(file_path, ".csv")
                    elif ".mtx" in fmt:
                        adata = load_input_dataset(file_path, ".mtx")
                    else:
                        adata = load_input_dataset(file_path, ".h5ad")

                    st.session_state["adata"] = adata
                    st.session_state.setdefault("pipeline_status", {})["Upload"] = "done"
                    st.success(f"✅ Loaded {size_gb:.2f} GB — {adata.n_obs:,} cells × {adata.n_vars:,} genes")
                except MemoryError:
                    st.error(
                        "The dataset is too large to load fully into memory in this environment. "
                        "Try more RAM or pre-filter the data before loading."
                    )
                except Exception as e:
                    st.error(f"Failed to read file: {e}")

# ──────────────────────────────────────────────────────────────────────────────
with tab_example:
    st.info("Load the built-in PBMC 3k dataset (2,700 cells, ~33k genes) for a full demo walkthrough.")
    col_a, col_b = st.columns([1, 2])
    with col_a:
        if st.button("🔬 Load PBMC 3k", type="primary"):
            with st.spinner("Downloading PBMC 3k (~60 MB)..."):
                adata = load_demo_dataset()
            st.session_state["adata"] = adata
            st.session_state.setdefault("pipeline_status", {})["Upload"] = "done"
            st.success("✅ PBMC 3k loaded!")
    with col_b:
        st.markdown("""
        **PBMC 3k** is the canonical scRNA-seq benchmark dataset (10x Genomics).
        Use it to test the full pipeline: QC → Clustering → CellTypist annotation → DE → Pathways.
        """)

# ── Dataset summary ──────────────────────────────────────────────────────────
adata = st.session_state.get("adata")
if adata is None:
    st.stop()

st.divider()
st.markdown("### 📊 Dataset Overview")

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Cells", f"{adata.n_obs:,}")
m2.metric("Total Genes", f"{adata.n_vars:,}")
m3.metric("Obs Columns", len(adata.obs.columns))
m4.metric("Var Columns", len(adata.var.columns))
m5.metric("Layers", len(adata.layers) if hasattr(adata, 'layers') else 0)

# Quick sanity estimate for RAM pressure if data were densified downstream.
estimated_dense_gb = (adata.n_obs * adata.n_vars * 4) / (1024 ** 3)
if estimated_dense_gb > 8:
    st.warning(
        f"Large dataset notice: dense matrix equivalent is about {estimated_dense_gb:,.1f} GB. "
        "Downstream operations may require high RAM; keep data sparse where possible."
    )

tab_obs, tab_var, tab_uns = st.tabs(["Cell Metadata (obs)", "Gene Metadata (var)", "Dataset Info (uns)"])

with tab_obs:
    st.dataframe(adata.obs.head(20), use_container_width=True)

with tab_var:
    st.dataframe(adata.var.head(20), use_container_width=True)

with tab_uns:
    if adata.uns:
        keys_info = {k: str(type(v).__name__) for k, v in adata.uns.items()}
        st.json(keys_info)
    else:
        st.info("No .uns metadata stored yet.")

render_nav_buttons(1)
