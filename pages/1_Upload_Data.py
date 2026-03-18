import streamlit as st
import scanpy as sc
import pandas as pd
import os
import shutil
import tempfile
import h5py

from utils.styles import inject_global_css, page_header, render_sidebar, render_nav_buttons
from utils.auth import get_current_user

# ── Register missing null-encoding reader (for files with None values in uns) ──
try:
    from anndata._io.specs.registry import _REGISTRY
    from anndata._io.specs import IOSpec as _IOSpec
    import h5py as _h5py

    _null_spec = _IOSpec("null", "0.1.0")

    @_REGISTRY.register_read(_h5py.Dataset, _null_spec)
    def _read_null_ds(elem):
        return None

    @_REGISTRY.register_read(_h5py.Group, _null_spec)
    def _read_null_grp(elem):
        return None
except Exception:
    pass  # already registered or future anndata handles it natively


def _load_h5ad_safe(path: str):
    """Load h5ad with progressive fallback strategies."""
    # Strategy 1: normal read
    try:
        return sc.read_h5ad(path)
    except Exception as e1:
        if "null" not in str(e1).lower() and "IORegistryError" not in str(type(e1).__name__):
            raise

    # Strategy 2: backed read (memory-maps the file, avoids parsing problematic uns)
    try:
        adata = sc.read_h5ad(path, backed="r")
        adata = adata.to_memory()
        return adata
    except Exception:
        pass

    # Strategy 3: read X / obs / var directly via h5py (no pytables needed)
    import anndata as ad
    import scipy.sparse as sp
    import numpy as np

    def _h5_to_df(grp) -> pd.DataFrame:
        """Convert an h5py Group (AnnData obs/var) to a DataFrame."""
        cols = {}
        index = None
        for key in grp.keys():
            val = grp[key]
            if isinstance(val, h5py.Dataset):
                try:
                    arr = val[()]
                    if arr.dtype.kind in ("S", "O"):
                        arr = arr.astype(str)
                    cols[key] = arr
                except Exception:
                    pass
        idx_name = grp.attrs.get("_index", None)
        if idx_name and idx_name in cols:
            index = cols.pop(idx_name)
        elif "_index" in grp:
            raw = grp["_index"][()]
            index = raw.astype(str) if raw.dtype.kind in ("S", "O") else raw
        return pd.DataFrame(cols, index=index)

    with h5py.File(path, "r") as f:
        x_group = f["X"]
        if isinstance(x_group, h5py.Dataset):
            X = x_group[()]
        else:
            data    = x_group["data"][()]
            indices = x_group["indices"][()]
            indptr  = x_group["indptr"][()]
            shape   = tuple(x_group.attrs.get("shape", (len(indptr) - 1, indices.max() + 1)))
            X = sp.csr_matrix((data, indices, indptr), shape=shape)

        obs = _h5_to_df(f["obs"]) if "obs" in f else pd.DataFrame()
        var = _h5_to_df(f["var"]) if "var" in f else pd.DataFrame()

    adata = ad.AnnData(X=X, obs=obs, var=var)
    return adata


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
    This means Streamlit is still running with the old file size limit.
    <b>Restart Streamlit</b> in your terminal to apply the 100 GB limit:<br>
    <code style="background:#161B22;padding:2px 8px;border-radius:4px;color:#00D4FF;">
    cd ~/python_lessons/scRNA_Explorer &amp;&amp; streamlit run app.py
    </code>
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
        st.info(f"📦 File: **{file.name}** ({file_size_mb:,.1f} MB) — reading...")
        tmp_path = None
        with st.spinner("Loading dataset into memory..."):
            try:
                suffix = ".loom" if file.name.lower().endswith(".loom") else ".h5ad"
                temp_dir = tempfile.gettempdir()
                _ensure_disk_space(file.size, temp_dir)

                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=temp_dir) as tmp:
                    # Stream in chunks to avoid loading huge uploads into RAM at once.
                    chunk_size = 64 * 1024 * 1024  # 64 MB
                    file.seek(0)
                    while True:
                        chunk = file.read(chunk_size)
                        if not chunk:
                            break
                        tmp.write(chunk)
                    tmp_path = tmp.name

                if suffix == ".loom":
                    adata = sc.read_loom(tmp_path)
                else:
                    adata = _load_h5ad_safe(tmp_path)
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
    Enter a path that exists <b>on the Linux server</b> (e.g. <code>/users/simon/data/file.h5ad</code>).<br>
    <b>If your file is on your Windows/Mac laptop</b> → use the <b>Browser Upload</b> tab instead
    (restart Streamlit first to enable 100 GB uploads).
    </span>
    </div>
    """, unsafe_allow_html=True)

    file_path = st.text_input(
        "Absolute server path (Linux)",
        placeholder="/users/simon/data/human_immune_health_atlas_dc.h5ad"
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
                        adata = sc.read_loom(file_path)
                    elif ".csv" in fmt:
                        adata = sc.read_csv(file_path).T
                    elif ".mtx" in fmt:
                        mtx_dir = os.path.dirname(file_path)
                        adata = sc.read_10x_mtx(mtx_dir, var_names="gene_symbols")
                    else:
                        adata = _load_h5ad_safe(file_path)

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
                adata = sc.datasets.pbmc3k()
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
