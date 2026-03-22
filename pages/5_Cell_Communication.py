"""
Cell-Cell Communication Analysis — NicheNet-inspired inference
Analyzes how cell types influence each other through ligand-receptor signaling
"""

import streamlit as st
import pandas as pd

from utils.styles import inject_global_css, page_header, render_sidebar, render_nav_buttons
from utils.cellcomm import (
    infer_sender_clusters, infer_receiver_clusters,
    infer_cell_communication, show_nichenet_communication_network,
    LIGAND_RECEPTOR_NETWORK
)

st.set_page_config(page_title="Cell Communication", layout="wide")
inject_global_css()
render_sidebar()

page_header(
    "📡", "Cell-Cell Communication Analysis",
    "NicheNet-inspired inference of cell-cell communication through ligand-receptor signaling"
)

adata = st.session_state.get("adata")
if adata is None:
    st.warning("⚠️ Please upload and analyze a dataset first (complete Steps 1-3).")
    st.stop()

if "leiden" not in adata.obs.columns:
    st.warning("⚠️ Run clustering (Step 3) before analyzing cell-cell communication.")
    st.stop()

# ── Learn about NicheNet ──────────────────────────────────────────────────────

with st.expander("📚 What is cell-cell communication analysis?", expanded=False):
    st.markdown("""
    ### NicheNet Principles

    This analysis identifies how different cell types influence each other through **signaling molecules**.

    **Three-Step Logic:**

    1. **Sender Cells**: Produce ligands (signaling molecules)
       - Express genes encoding TNF, IFNG, IL2, etc.
       - Send signals to neighboring cells

    2. **Receivers Cells**: Receive signals via receptors
       - Express genes encoding TNFR1, IFNGR1, IL2RA, etc.
       - Activated by ligands from sender cells

    3. **Downstream Effects**: Signaling changes gene expression
       - Ligand-receptor binding triggers pathways
       - Affects expression of target genes in receiver cells
       - Example: TNF → TNFR1 → upregulates IL6, IL8, ICAM1

    **Key Concept:**
    > "Cluster A may influence Cluster B through signaling molecules (ligands) that affect gene expression."

    **Example Communication Loop:**
    ```
    Macrophage (TNF producer)
         ↓ [TNF ligand]
    T Cell (TNFR1 receiver)
         ↓ [Signaling cascade]
    T Cell expression changes: ↑IL2, ↑IFNG, ↑TNF
    Amplifies immune response
    ```
    """)

# ── Display Communication Network ──────────────────────────────────────────────

st.divider()
show_nichenet_communication_network(adata)

# ── Ligand-Receptor Database Info ─────────────────────────────────────────────

st.divider()
st.markdown("## 📖 Ligand-Receptor Pairs Database")

with st.expander("View all curated ligand-receptor pairs", expanded=False):
    pair_list = []
    for pair_key, info in LIGAND_RECEPTOR_NETWORK.items():
        pair_list.append({
            "Pair": pair_key,
            "Ligand": info["ligand"],
            "Receptor": info["receptor"],
            "Context": info["context"],
            "Targets": ", ".join(list(info.get("target_genes", {}).keys())[:3])
        })

    pairs_df = pd.DataFrame(pair_list)
    st.dataframe(pairs_df, use_container_width=True)

    st.caption("""
    **Column Descriptions:**
    - **Pair**: Ligand-Receptor interaction code
    - **Ligand**: Gene encoding the signaling molecule
    - **Receptor**: Gene encoding the receptor
    - **Context**: Biological role of this signaling
    - **Targets**: Top 3 downstream target genes affected
    """)

# ── Statistical Summary ────────────────────────────────────────────────────────

st.divider()
st.markdown("## 📊 Communication Summary")

senders = infer_sender_clusters(adata, "leiden")
receivers = infer_receiver_clusters(adata, "leiden")

summary_data = {
    "Category": ["Sender Clusters", "Receiver Clusters", "Possible Interfaces"],
    "Count": [len(senders), len(receivers), len(senders) * len(receivers) if senders and receivers else 0],
    "Interpretation": [
        "Clusters expressing ligands",
        "Clusters expressing receptors",
        "Sender-Receiver pairs to explore"
    ]
}

summary_df = pd.DataFrame(summary_data)
st.dataframe(summary_df, use_container_width=True)

# ── Sender & Receiver Details ──────────────────────────────────────────────────

if senders:
    st.markdown("### Sender Cell Clusters (Ligand Producers)")
    for cluster_id, info in senders.items():
        with st.expander(f"🔴 Cluster {cluster_id} — {len(info['ligands'])} ligand(s)", expanded=False):
            st.markdown(f"- **Cell Count**: {info['n_cells']}")
            st.markdown(f"- **Role**: {info['role']}")

            ligand_df = pd.DataFrame([
                {
                    "Ligand": ligand,
                    "Mean Expr": f"{expr['mean_expr']:.2f}",
                    "% Expressed": f"{expr['pct_expressed']:.1f}%"
                }
                for ligand, expr in info['ligands'].items()
            ])
            st.dataframe(ligand_df, use_container_width=True)

if receivers:
    st.markdown("### Receiver Cell Clusters (Receptor Expressers)")
    for cluster_id, info in receivers.items():
        with st.expander(f"🔵 Cluster {cluster_id} — {len(info['receptors'])} receptor(s)", expanded=False):
            st.markdown(f"- **Cell Count**: {info['n_cells']}")
            st.markdown(f"- **Role**: {info['role']}")

            receptor_df = pd.DataFrame([
                {
                    "Receptor": receptor,
                    "Mean Expr": f"{expr['mean_expr']:.2f}",
                    "% Expressed": f"{expr['pct_expressed']:.1f}%"
                }
                for receptor, expr in info['receptors'].items()
            ])
            st.dataframe(receptor_df, use_container_width=True)

# ── Next Steps ─────────────────────────────────────────────────────────────────

st.divider()
st.markdown("## 🎯 Next Steps")

st.markdown("""
**Validate Findings:**
1. Review ligand and receptor expression in UMAP plots (Gene Explorer - Step 5)
2. Check if target genes are upregulated in receiver clusters
3. Confirm predictions with literature (does interaction make biological sense?)

**Biological Questions to Ask:**
- Which signals are most important in your system?
- Do senders and receivers physically interact in tissue?
- Could blocking specific interactions change cell behavior?
- Are communication patterns disrupted in disease?

**Further Analysis:**
- Perform spatial analysis if tissue coordinates available
- Check temporal dynamics if time-series data exists
- Integrate with single-cell trajectory inference
- Compare communication networks between conditions
""")

render_nav_buttons(6)
