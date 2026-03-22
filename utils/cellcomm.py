"""
NicheNet-inspired cell-cell communication analysis.
Identifies sender/receiver cells and infers communication based on ligand-receptor-target relationships.
Rule-based approach without external APIs.
"""

import pandas as pd
import numpy as np
import streamlit as st
from typing import Dict, List, Tuple, Set


# Ligand-Receptor pairs with downstream target genes (canonical signaling targets)
LIGAND_RECEPTOR_NETWORK = {
    "TNF-TNFR1": {
        "ligand": "TNF",
        "receptor": "TNFR1",
        "ligand_full": "Tumor Necrosis Factor",
        "receptor_full": "TNF Receptor 1",
        "description": "Pro-inflammatory cytokine signaling",
        "context": "Inflammatory response, immune activation",
        "target_genes": {
            "IL6": "Interleukin 6 (amplifies inflammation)",
            "IL8": "Interleukin 8 (neutrophil recruitment)",
            "ICAM1": "Intercellular Adhesion Molecule (cell adhesion)",
            "CXCL10": "Chemokine (immune cell recruitment)",
            "MCP1": "Monocyte Chemoattractant Protein",
        }
    },
    "IFNG-IFNGR1": {
        "ligand": "IFNG",
        "receptor": "IFNGR1",
        "ligand_full": "Interferon Gamma",
        "receptor_full": "IFN-Gamma Receptor 1",
        "description": "Interferon signaling",
        "context": "Immune defense, macrophage activation",
        "target_genes": {
            "HLA-DRA": "MHC Class II (antigen presentation)",
            "IRGS": "Interferon-responsive genes (immune response)",
            "IDO1": "Indoleamine 2,3-dioxygenase (immune regulation)",
            "STAT1": "Signal Transducer and Activator (IFN signaling)",
            "GBP1": "GTPase (intracellular immunity)",
        }
    },
    "IL2-IL2RA": {
        "ligand": "IL2",
        "receptor": "IL2RA",
        "ligand_full": "Interleukin 2",
        "receptor_full": "IL-2 Receptor Alpha",
        "description": "T cell growth factor",
        "context": "T cell expansion and activation",
        "target_genes": {
            "IFNG": "Interferon Gamma (T cell effector)",
            "TNF": "Tumor Necrosis Factor (T cell activation)",
            "GZMA": "Granzyme A (cytotoxicity)",
            "PRF1": "Perforin (cytotoxicity)",
            "FCER1G": "Fc Receptor Gamma (immune signaling)",
        }
    },
    "VEGFA-FLT1": {
        "ligand": "VEGFA",
        "receptor": "FLT1",
        "ligand_full": "Vascular Endothelial Growth Factor A",
        "receptor_full": "Fms-related Tyrosine Kinase 1",
        "description": "Angiogenesis and vascular development",
        "context": "Vessel formation, endothelial cell activation",
        "target_genes": {
            "PDGFB": "Platelet-derived Growth Factor (SMC recruitment)",
            "ANGPT1": "Angiopoietin 1 (vascular maturation)",
            "CDH5": "Cadherin 5 (cell-cell adhesion)",
            "KDR": "Kinase Insert Domain Receptor (angiogenic signaling)",
            "FLK1": "Fetal Liver Kinase 1 (VEGF co-receptor)",
        }
    },
    "FGF1-FGFR1": {
        "ligand": "FGF1",
        "receptor": "FGFR1",
        "ligand_full": "Fibroblast Growth Factor 1",
        "receptor_full": "FGF Receptor 1",
        "description": "Fibroblast signaling",
        "context": "Cell proliferation, tissue repair",
        "target_genes": {
            "MMP2": "Matrix Metalloproteinase 2 (ECM remodeling)",
            "COL1A1": "Collagen Type I (ECM production)",
            "TIMP1": "TIMP Metallopeptidase Inhibitor (ECM regulation)",
            "CTGF": "Connective Tissue Growth Factor (fibrosis)",
            "SMA": "Smooth Muscle Actin (myofibroblast marker)",
        }
    },
    "PDGFA-PDGFRA": {
        "ligand": "PDGFA",
        "receptor": "PDGFRA",
        "ligand_full": "Platelet-derived Growth Factor A",
        "receptor_full": "PDGF Receptor Alpha",
        "description": "Cell growth and migration",
        "context": "Mesenchymal cell recruitment, fibrosis",
        "target_genes": {
            "MMP9": "Matrix Metalloproteinase 9 (invasion)",
            "ACTA2": "Actin Alpha 2 (myofibroblast)",
            "POSTN": "Periostin (fibrosis)",
            "FAP": "Fibroblast Activation Protein (CAF marker)",
            "ITGA5": "Integrin Alpha 5 (cell adhesion)",
        }
    },
    "CDH1-CDH1": {
        "ligand": "CDH1",
        "receptor": "CDH1",
        "ligand_full": "E-Cadherin",
        "receptor_full": "E-Cadherin receptor",
        "description": "Homophilic cell-cell adhesion",
        "context": "Cell-cell contacts, tissue organization",
        "target_genes": {
            "CTNNB1": "Beta-catenin (adhesion signaling)",
            "CDH3": "Cadherin 3 (cell adhesion)",
            "ZO1": "Zonula Occludens-1 (tight junctions)",
            "OCLN": "Occludin (tight junctions)",
        }
    },
    "ICAM1-ITGAM": {
        "ligand": "ICAM1",
        "receptor": "ITGAM",
        "ligand_full": "Intercellular Adhesion Molecule 1",
        "receptor_full": "Integrin Alpha M",
        "description": "Immune cell recruitment and adhesion",
        "context": "Leukocyte extravasation, immune response",
        "target_genes": {
            "TNF": "Tumor Necrosis Factor (activation)",
            "IL1B": "Interleukin 1 Beta (inflammation)",
            "ROS1": "Reactive Oxygen Species production",
            "LYZ": "Lysozyme (antimicrobial)",
        }
    },
}

# Cell type profiles: which ligands and receptors they express
CELL_TYPE_PROFILES = {
    "T cell": {
        "ligands": ["IL2", "IFNG", "TNF", "FASL"],
        "receptors": ["IL2RA", "TNFR1", "IFNGR1"],
        "role": "Immune effector cell"
    },
    "Macrophage": {
        "ligands": ["TNF", "IL6", "IL1B"],
        "receptors": ["TNFR1", "IL1R1", "IFNGR1"],
        "role": "Innate immune and antigen-presenting cell"
    },
    "NK cell": {
        "ligands": ["IFNG", "TNF", "FASL"],
        "receptors": ["TNFR1", "IFNGR1"],
        "role": "Cytotoxic immune cell"
    },
    "Fibroblast": {
        "ligands": ["PDGFA", "FGF1", "VEGFA"],
        "receptors": ["PDGFRA", "FGFR1", "TNFR1"],
        "role": "ECM-producing stromal cell"
    },
    "Endothelial": {
        "ligands": ["VEGFA", "FGF1"],
        "receptors": ["FLT1", "FGFR1", "PDGFRA"],
        "role": "Vascular cell"
    },
    "B cell": {
        "ligands": ["IL2", "TNF"],
        "receptors": ["TNFR1", "IL1R1"],
        "role": "Antibody-producing cell"
    },
    "Dendritic cell": {
        "ligands": ["IL6", "TNF"],
        "receptors": ["IFNGR1", "TNFR1"],
        "role": "Antigen-presenting cell"
    },
}


def infer_sender_clusters(adata, cluster_col: str = "leiden") -> Dict[str, Dict]:
    """
    Identify sender clusters based on ligand expression.

    NicheNet logic: Sender cells express ligands that signal to neighbors.
    """
    if cluster_col not in adata.obs.columns:
        return {}

    senders = {}
    ligand_genes = set()

    # Collect all ligand genes
    for pair_info in LIGAND_RECEPTOR_NETWORK.values():
        ligand_genes.add(pair_info["ligand"])

    # Check each cluster
    for cluster_id in adata.obs[cluster_col].unique():
        cluster_data = adata[adata.obs[cluster_col] == cluster_id]

        ligand_expr = {}
        for ligand in ligand_genes:
            if ligand in adata.var_names:
                expr_vec = cluster_data[:, ligand].X
                if hasattr(expr_vec, 'toarray'):
                    expr_vec = expr_vec.toarray().flatten()
                else:
                    expr_vec = np.asarray(expr_vec).flatten()

                mean_expr = np.mean(expr_vec)
                pct_expressed = 100 * np.sum(expr_vec > 0) / len(expr_vec)

                if mean_expr > 0.1 and pct_expressed > 10:  # Expressed in >10% of cells
                    ligand_expr[ligand] = {
                        "mean_expr": mean_expr,
                        "pct_expressed": pct_expressed
                    }

        if ligand_expr:
            senders[cluster_id] = {
                "ligands": ligand_expr,
                "n_cells": len(cluster_data),
                "role": "Ligand-producing (sender) cell cluster"
            }

    return senders


def infer_receiver_clusters(adata, cluster_col: str = "leiden") -> Dict[str, Dict]:
    """
    Identify receiver clusters based on receptor expression.

    NicheNet logic: Receiver cells express receptors that receive signals from neighbors.
    """
    if cluster_col not in adata.obs.columns:
        return {}

    receivers = {}
    receptor_genes = set()

    # Collect all receptor genes
    for pair_info in LIGAND_RECEPTOR_NETWORK.values():
        receptor_genes.add(pair_info["receptor"])

    # Check each cluster
    for cluster_id in adata.obs[cluster_col].unique():
        cluster_data = adata[adata.obs[cluster_col] == cluster_id]

        receptor_expr = {}
        for receptor in receptor_genes:
            if receptor in adata.var_names:
                expr_vec = cluster_data[:, receptor].X
                if hasattr(expr_vec, 'toarray'):
                    expr_vec = expr_vec.toarray().flatten()
                else:
                    expr_vec = np.asarray(expr_vec).flatten()

                mean_expr = np.mean(expr_vec)
                pct_expressed = 100 * np.sum(expr_vec > 0) / len(expr_vec)

                if mean_expr > 0.1 and pct_expressed > 10:  # Expressed in >10% of cells
                    receptor_expr[receptor] = {
                        "mean_expr": mean_expr,
                        "pct_expressed": pct_expressed
                    }

        if receptor_expr:
            receivers[cluster_id] = {
                "receptors": receptor_expr,
                "n_cells": len(cluster_data),
                "role": "Receptor-expressing (receiver) cell cluster"
            }

    return receivers


def infer_cell_communication(adata, sender_id, receiver_id) -> pd.DataFrame:
    """
    Infer communication from sender to receiver cluster using NicheNet logic.

    Returns interactions with target genes that would be affected.
    """
    if "leiden" not in adata.obs.columns:
        return pd.DataFrame()

    sender_data = adata[adata.obs["leiden"] == sender_id]
    receiver_data = adata[adata.obs["leiden"] == receiver_id]

    if len(sender_data) == 0 or len(receiver_data) == 0:
        return pd.DataFrame()

    interactions = []

    # Check each ligand-receptor pair
    for pair_key, pair_info in LIGAND_RECEPTOR_NETWORK.items():
        ligand = pair_info["ligand"]
        receptor = pair_info["receptor"]

        if ligand not in adata.var_names or receptor not in adata.var_names:
            continue

        # Check sender expresses ligand
        ligand_expr = sender_data[:, ligand].X
        if hasattr(ligand_expr, 'toarray'):
            ligand_expr = ligand_expr.toarray().flatten()
        else:
            ligand_expr = np.asarray(ligand_expr).flatten()

        sender_ligand_level = np.mean(ligand_expr)

        # Check receiver expresses receptor
        receptor_expr = receiver_data[:, receptor].X
        if hasattr(receptor_expr, 'toarray'):
            receptor_expr = receptor_expr.toarray().flatten()
        else:
            receptor_expr = np.asarray(receptor_expr).flatten()

        receiver_receptor_level = np.mean(receptor_expr)

        # Only include if both are expressed
        if sender_ligand_level > 0 and receiver_receptor_level > 0:
            interaction_score = sender_ligand_level * receiver_receptor_level

            # Get target genes that would be affected
            target_genes = pair_info.get("target_genes", {})

            interactions.append({
                "Pair": pair_key,
                "Ligand": ligand,
                "Receptor": receptor,
                "Ligand Expression": f"{sender_ligand_level:.2f}",
                "Receptor Expression": f"{receiver_receptor_level:.2f}",
                "Interaction Score": f"{interaction_score:.2f}",
                "Target Genes": ", ".join(list(target_genes.keys())[:3]),
                "Description": pair_info.get("description", ""),
            })

    return pd.DataFrame(interactions)


def get_downstream_targets(pair_key: str) -> Dict[str, str]:
    """
    Get downstream target genes affected by a ligand-receptor pair.

    NicheNet logic: Identifies genes whose expression changes in response to signaling.
    """
    if pair_key not in LIGAND_RECEPTOR_NETWORK:
        return {}

    return LIGAND_RECEPTOR_NETWORK[pair_key].get("target_genes", {})


def generate_nichenet_explanation(sender_id, receiver_id, pair_key: str,
                                 adata=None) -> str:
    """
    Generate NicheNet-style explanation of cell-cell communication.

    Output format:
    "Cluster A may influence Cluster B through signaling molecules (ligands)
     that affect gene expression."
    """
    if pair_key not in LIGAND_RECEPTOR_NETWORK:
        return "Unknown interaction"

    pair_info = LIGAND_RECEPTOR_NETWORK[pair_key]
    ligand = pair_info["ligand"]
    receptor = pair_info["receptor"]
    target_genes = pair_info.get("target_genes", {})
    context = pair_info.get("context", "Cell communication")

    # Get target gene descriptions
    target_desc = ""
    if target_genes:
        top_targets = list(target_genes.items())[:2]
        target_desc = " → ".join([f"**{gene}** ({desc})" for gene, desc in top_targets])

    explanation = f"""
    ### 📡 NicheNet Inference: Cluster {sender_id} → Cluster {receiver_id}

    **Mechanism:**
    - **Cluster {sender_id}** produces **{pair_info['ligand_full']}** (ligand)
    - **Cluster {receiver_id}** expresses **{pair_info['receptor_full']}** (receptor)
    - Ligand-receptor binding triggers signaling cascade

    **Effect on Cluster {receiver_id}:**
    Cluster {sender_id} may influence Cluster {receiver_id} through **{ligand}** signaling,
    which would affect downstream gene expression including:
    {target_desc if target_desc else "Multiple target genes"}

    **Biological Context:**
    {context}

    **Predicted Outcomes:**
    - Changes in cell state or behavior in {receiver_id}
    - Potential upregulation of target genes in receiver cells
    - Possible feedback regulation through downstream signals
    """

    return explanation


def show_nichenet_communication_network(adata) -> None:
    """
    Display comprehensive NicheNet-style cell-cell communication network.
    """
    if "leiden" not in adata.obs.columns:
        st.warning("Run clustering first to analyze cell-cell communication")
        return

    st.markdown("## 📡 Cell-Cell Communication Network (NicheNet-inspired)")

    # Identify senders and receivers
    senders = infer_sender_clusters(adata, "leiden")
    receivers = infer_receiver_clusters(adata, "leiden")

    if not senders:
        st.info("No clear sender cells detected. Try different resolution clustering.")
        return

    if not receivers:
        st.info("No clear receiver cells detected. Try different resolution clustering.")
        return

    # Summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Sender Clusters", len(senders))
    with col2:
        st.metric("Receiver Clusters", len(receivers))
    with col3:
        st.metric("Possible Interactions", len(senders) * len(receivers))

    st.divider()

    # Interaction analysis
    st.markdown("### Predicted Ligand-Receptor Interactions")

    sender_options = {f"Cluster {cid} ({info['n_cells']} cells)": cid
                     for cid, info in senders.items()}
    receiver_options = {f"Cluster {cid} ({info['n_cells']} cells)": cid
                       for cid, info in receivers.items()}

    col1, col2 = st.columns(2)
    with col1:
        sender_display = st.selectbox("Sender Cluster", list(sender_options.keys()))
        sender_id = sender_options[sender_display]

    with col2:
        receiver_display = st.selectbox("Receiver Cluster", list(receiver_options.keys()))
        receiver_id = receiver_options[receiver_display]

    if sender_id and receiver_id:
        interactions = infer_cell_communication(adata, sender_id, receiver_id)

        if not interactions.empty:
            st.success(f"🔗 Found {len(interactions)} potential interaction(s)")

            # Display each interaction with NicheNet explanation
            for idx, row in interactions.iterrows():
                pair_key = row["Pair"]

                with st.expander(
                    f"🧬 {pair_key} | Score: {row['Interaction Score']}",
                    expanded=(idx == 0)
                ):
                    # NicheNet explanation
                    explanation = generate_nichenet_explanation(
                        sender_id, receiver_id, pair_key, adata
                    )
                    st.markdown(explanation)

                    # Target genes
                    targets = get_downstream_targets(pair_key)
                    if targets:
                        st.markdown("**Downstream Target Genes:**")
                        for gene, function in targets.items():
                            st.markdown(f"- **{gene}**: {function}")
        else:
            st.info("No interactions detected between selected clusters")
