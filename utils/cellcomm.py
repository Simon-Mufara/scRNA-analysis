"""
Cell-cell communication analysis using curated ligand-receptor pairs.
Identifies potential interactions between cell types based on gene expression.
"""

import pandas as pd
import numpy as np
import streamlit as st
from typing import Dict, List, Tuple


# Curated ligand-receptor database (simplified, high-confidence pairs)
LIGAND_RECEPTOR_PAIRS = {
    "TNF-TNFR1": {
        "ligand": "TNF",
        "receptor": "TNFR1",
        "ligand_full": "Tumor Necrosis Factor",
        "receptor_full": "TNF Receptor 1",
        "description": "Pro-inflammatory cytokine signaling",
        "context": "Inflammatory response, immune activation"
    },
    "IFNG-IFNGR1": {
        "ligand": "IFNG",
        "receptor": "IFNGR1",
        "ligand_full": "Interferon Gamma",
        "receptor_full": "IFN-Gamma Receptor 1",
        "description": "Interferon signaling",
        "context": "Immune defense, macrophage activation"
    },
    "IL2-IL2RA": {
        "ligand": "IL2",
        "receptor": "IL2RA",
        "ligand_full": "Interleukin 2",
        "receptor_full": "IL-2 Receptor Alpha",
        "description": "T cell growth factor",
        "context": "T cell expansion and activation"
    },
    "VEGFA-FLT1": {
        "ligand": "VEGFA",
        "receptor": "FLT1",
        "ligand_full": "Vascular Endothelial Growth Factor A",
        "receptor_full": "Fms-related Tyrosine Kinase 1",
        "description": "Angiogenesis and vascular development",
        "context": "Vessel formation, endothelial cell activation"
    },
    "FGF1-FGFR1": {
        "ligand": "FGF1",
        "receptor": "FGFR1",
        "ligand_full": "Fibroblast Growth Factor 1",
        "receptor_full": "FGF Receptor 1",
        "description": "Fibroblast signaling",
        "context": "Cell proliferation, tissue repair"
    },
    "PDGFA-PDGFRA": {
        "ligand": "PDGFA",
        "receptor": "PDGFRA",
        "ligand_full": "Platelet-derived Growth Factor A",
        "receptor_full": "PDGF Receptor Alpha",
        "description": "Cell growth and migration",
        "context": "Mesenchymal cell recruitment, fibrosis"
    },
    "CDH1-CDH1": {
        "ligand": "CDH1",
        "receptor": "CDH1",
        "ligand_full": "E-Cadherin (Calcium-dependent cell adhesion protein)",
        "receptor_full": "E-Cadherin receptor",
        "description": "Homophilic cell-cell adhesion",
        "context": "Cell-cell contacts, tissue organization"
    },
    "ICAM1-ITGAM": {
        "ligand": "ICAM1",
        "receptor": "ITGAM",
        "ligand_full": "Intercellular Adhesion Molecule 1",
        "receptor_full": "Integrin Alpha M",
        "description": "Immune cell recruitment and adhesion",
        "context": "Leukocyte extravasation, immune response"
    },
}

# Cell type expressing common ligands
CELL_TYPE_LIGANDS = {
    "T cell": ["IL2", "IFNG", "TNF"],
    "Macrophage": ["TNF", "IL6", "IL1B"],
    "NK cell": ["IFNG", "TNF", "FASL"],
    "Fibroblast": ["PDGFA", "FGF1", "VEGFA"],
    "Endothelial": ["VEGFA", "FGF1"],
    "B cell": ["IL2", "TNF"],
}

# Cell type expressing common receptors
CELL_TYPE_RECEPTORS = {
    "T cell": ["IL2RA", "TNFR1", "IFNGR1"],
    "Macrophage": ["TNFR1", "IL1R1", "IFNGR1"],
    "Endothelial": ["FLT1", "FGFR1", "PDGFRA"],
    "Fibroblast": ["PDGFRA", "FGFR1", "TNFR1"],
    "NK cell": ["TNFR1", "IFNGR1"],
    "B cell": ["TNFR1", "IL1R1"],
}


def get_ligand_receptor_info(pair_key: str) -> Dict:
    """
    Get detailed information about a ligand-receptor pair.

    Args:
        pair_key: Key from LIGAND_RECEPTOR_PAIRS dict

    Returns:
        Dictionary with full pair information
    """
    return LIGAND_RECEPTOR_PAIRS.get(pair_key, {})


def render_ligand_tooltip(pair_key: str) -> str:
    """
    Create a tooltip explanation for a ligand-receptor pair.

    Returns formatted markdown/HTML for the tooltip
    """
    pair_info = get_ligand_receptor_info(pair_key)
    if not pair_info:
        return "Unknown pair"

    return f"""
    <div style="background:rgba(22,27,34,0.8);border:1px solid #21262D;border-radius:8px;padding:12px;max-width:300px;">
        <div style="font-weight:700;color:#00D4FF;margin-bottom:8px;">{pair_key}</div>
        <div style="color:#E6EDF3;font-size:0.85rem;margin-bottom:6px;">
            <b>Ligand:</b> {pair_info.get('ligand_full', pair_info.get('ligand', 'Unknown'))}
        </div>
        <div style="color:#E6EDF3;font-size:0.85rem;margin-bottom:6px;">
            <b>Receptor:</b> {pair_info.get('receptor_full', pair_info.get('receptor', 'Unknown'))}
        </div>
        <div style="color:#8B949E;font-size:0.8rem;margin-bottom:6px;">
            {pair_info.get('description', 'Cell-cell signaling')}
        </div>
        <div style="color:#6E7681;font-size:0.75rem;font-style:italic;">
            Context: {pair_info.get('context', 'Cell communication')}
        </div>
    </div>
    """


def identify_cell_communication(adata, sender_cell_type: str, receiver_cell_type: str) -> pd.DataFrame:
    """
    Identify potential cell-cell communication between two cell types.

    Args:
        adata: AnnData object with cell_type annotations
        sender_cell_type: Expressing cell type
        receiver_cell_type: Receiving cell type

    Returns:
        DataFrame with potential interactions
    """
    if "cell_type" not in adata.obs.columns:
        return pd.DataFrame()

    interactions = []

    # Get cells of each type
    sender_cells = adata[adata.obs["cell_type"] == sender_cell_type]
    receiver_cells = adata[adata.obs["cell_type"] == receiver_cell_type]

    if len(sender_cells) == 0 or len(receiver_cells) == 0:
        return pd.DataFrame()

    # Check each known ligand-receptor pair
    for pair_key, pair_info in LIGAND_RECEPTOR_PAIRS.items():
        ligand = pair_info.get("ligand")
        receptor = pair_info.get("receptor")

        if ligand not in adata.var_names or receptor not in adata.var_names:
            continue

        # Calculate mean expression in each cell type
        ligand_expr_sender = sender_cells[:, ligand].X
        if hasattr(ligand_expr_sender, 'toarray'):
            ligand_expr_sender = ligand_expr_sender.toarray().flatten()
        else:
            ligand_expr_sender = np.asarray(ligand_expr_sender).flatten()
        ligand_sender = np.mean(ligand_expr_sender)

        receptor_expr_receiver = receiver_cells[:, receptor].X
        if hasattr(receptor_expr_receiver, 'toarray'):
            receptor_expr_receiver = receptor_expr_receiver.toarray().flatten()
        else:
            receptor_expr_receiver = np.asarray(receptor_expr_receiver).flatten()
        receptor_receiver = np.mean(receptor_expr_receiver)

        # Only include if both are expressed
        if ligand_sender > 0 and receptor_receiver > 0:
            interaction_score = ligand_sender * receptor_receiver
            interactions.append({
                "Pair": pair_key,
                "Ligand": ligand,
                "Receptor": receptor,
                "Ligand Expr (Sender)": f"{ligand_sender:.2f}",
                "Receptor Expr (Receiver)": f"{receptor_receiver:.2f}",
                "Interaction Score": f"{interaction_score:.2f}",
                "Description": pair_info.get("description", ""),
            })

    return pd.DataFrame(interactions)


def get_sender_receiver_overview(adata) -> Dict[str, List[str]]:
    """
    Get overview of which cell types are likely senders and receivers.

    Returns:
        Dictionary with sender and receiver cell types
    """
    if "cell_type" not in adata.obs.columns:
        return {"senders": [], "receivers": []}

    senders = []
    receivers = []

    cell_types = adata.obs["cell_type"].unique()

    for cell_type in cell_types:
        # Check if likely sender (expresses ligands)
        cell_data = adata[adata.obs["cell_type"] == cell_type]

        ligand_genes = [lr.split("-")[0] for lr in LIGAND_RECEPTOR_PAIRS.keys()]
        receptor_genes = [lr.split("-")[1] for lr in LIGAND_RECEPTOR_PAIRS.keys()]

        ligands_found = [g for g in ligand_genes if g in adata.var_names]
        receptors_found = [g for g in receptor_genes if g in adata.var_names]

        if ligands_found:
            ligand_expr = [
                np.mean(cell_data[:, g].X.toarray().flatten()) if hasattr(cell_data[:, g].X, 'toarray')
                else np.mean(cell_data[:, g].X) for g in ligands_found
            ]
            if np.mean(ligand_expr) > 0.1:
                senders.append(cell_type)

        if receptors_found:
            receptor_expr = [
                np.mean(cell_data[:, g].X.toarray().flatten()) if hasattr(cell_data[:, g].X, 'toarray')
                else np.mean(cell_data[:, g].X) for g in receptors_found
            ]
            if np.mean(receptor_expr) > 0.1:
                receivers.append(cell_type)

    return {
        "senders": list(set(senders)),
        "receivers": list(set(receivers)),
    }


def show_cell_communication_panel(adata, sender_type: str, receiver_type: str) -> None:
    """
    Display comprehensive cell-cell communication panel with explanations.

    Args:
        adata: AnnData object
        sender_type: Sender cell type
        receiver_type: Receiver cell type
    """
    st.markdown(f"### 📡 Communication: {sender_type} → {receiver_type}")

    interactions_df = identify_cell_communication(adata, sender_type, receiver_type)

    if interactions_df.empty:
        st.info(f"No known interactions between {sender_type} and {receiver_type}")
        return

    st.markdown(f"**Found {len(interactions_df)} potential interactions:**")

    # Display interactions with tooltips
    for idx, row in interactions_df.iterrows():
        with st.expander(f"🔗 {row['Pair']} — {row['Description']}", expanded=False):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"""
                **Ligand → Receptor**
                - **{row['Ligand']}** ({row['Ligand Expr (Sender)']}) → **{row['Receptor']}** ({row['Receptor Expr (Receiver)']})
                - Interaction Score: {row['Interaction Score']}
                - {row['Description']}
                """)

                # Show biological context
                pair_info = get_ligand_receptor_info(row['Pair'])
                st.markdown(f"**Biological Context:** {pair_info.get('context', 'Cell communication')}")

            with col2:
                st.markdown("**Pathway Role:**")
                pair_info = get_ligand_receptor_info(row['Pair'])
                if "TNF" in row['Ligand'] or "TNF" in row['Receptor']:
                    st.markdown("🛡️ Inflammation")
                elif "IL" in row['Ligand'] or "IL" in row['Receptor']:
                    st.markdown("🔄 Immune signaling")
                elif "VEGF" in row['Ligand'] or "FLT" in row['Receptor']:
                    st.markdown("🧬 Angiogenesis")
                elif "FGF" in row['Ligand'] or "FGF" in row['Receptor']:
                    st.markdown("📊 Growth signaling")
                else:
                    st.markdown("📡 Cell adhesion")
