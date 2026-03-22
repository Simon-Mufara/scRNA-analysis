"""Debug page to trace session state and data flow"""
import streamlit as st
import numpy as np

st.set_page_config(page_title="Debug - Session State", layout="wide")

st.title("🔧 Debug - Session State & Data Flow")

st.markdown("---")
st.markdown("### 📊 Current Session State")

# Show all session state keys
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("**Session State Keys:**")
    if st.session_state:
        for key in st.session_state.keys():
            st.write(f"- `{key}`")
    else:
        st.warning("Session state is empty!")

with col2:
    st.markdown("**adata Object:**")
    adata = st.session_state.get("adata")
    if adata is None:
        st.error("❌ **adata is None** - no dataset loaded")
    else:
        st.success(f"✅ **adata exists**")
        st.write(f"- Shape: {adata.shape}")
        st.write(f"- X type: {type(adata.X)}")
        st.write(f"- X shape: {adata.X.shape}")
        st.write(f"- obs columns: {list(adata.obs.columns)[:5]}")

st.markdown("---")
st.markdown("### 🔍 Full Session State Details")

with st.expander("Click to expand - all session variables"):
    for key, value in st.session_state.items():
        if key == "adata":
            st.write(f"**{key}**: AnnData object ({value.shape})")
        elif isinstance(value, (str, int, float, bool)):
            st.write(f"**{key}**: {value}")
        elif isinstance(value, dict):
            st.write(f"**{key}**: dict with {len(value)} keys")
        elif isinstance(value, list):
            st.write(f"**{key}**: list with {len(value)} items")
        else:
            st.write(f"**{key}**: {type(value).__name__}")

st.markdown("---")
st.markdown("### 🧪 Quick Test")

test_col1, test_col2 = st.columns([1, 1])

with test_col1:
    if st.button("Test: Create dummy adata and save to session"):
        import numpy as np
        from anndata import AnnData

        X = np.random.poisson(5, size=(100, 500))
        adata_test = AnnData(X=X)
        adata_test.var_names = [f"Gene_{i}" for i in range(500)]
        adata_test.obs_names = [f"Cell_{i}" for i in range(100)]

        st.session_state["adata"] = adata_test
        st.success("✅ Dummy adata saved to session!")
        st.rerun()

with test_col2:
    if st.button("Test: Check if adata persists"):
        adata = st.session_state.get("adata")
        if adata is not None:
            st.success(f"✅ adata persists in session! Shape: {adata.shape}")
        else:
            st.error("❌ adata is None - session state not persisting!")

st.markdown("---")
st.markdown("### 📍 Navigation")
st.write("Go to:")
st.write("1. [Upload Data](pages/1_Upload_Data.py)")
st.write("2. [Quality Control](pages/2_Quality_Control.py)")
st.write("3. [Clustering](pages/3_Clustering_UMAP.py)")
