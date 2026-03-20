from __future__ import annotations

from typing import Dict, Iterable, List


CELL_TYPE_HINTS: Dict[str, List[str]] = {
    "T cells": ["CD3D", "CD3E", "TRBC1", "TRBC2", "IL7R"],
    "CD8 T cells": ["CD8A", "CD8B", "NKG7", "GZMB", "PRF1"],
    "Regulatory T cells": ["FOXP3", "IL2RA", "CTLA4", "TIGIT"],
    "B cells": ["MS4A1", "CD79A", "CD79B", "CD19", "BANK1"],
    "Plasma cells": ["MZB1", "SDC1", "XBP1", "JCHAIN"],
    "NK cells": ["NKG7", "GNLY", "KLRD1", "FCGR3A", "TRAC"],
    "Monocytes": ["LYZ", "S100A8", "S100A9", "FCN1", "LST1"],
    "Dendritic cells": ["FCER1A", "CLEC10A", "HLA-DRA", "IRF8"],
    "Macrophages": ["CD68", "APOE", "C1QA", "C1QB", "MRC1"],
    "Endothelial cells": ["PECAM1", "VWF", "KDR", "CLDN5"],
    "Fibroblasts": ["COL1A1", "COL3A1", "DCN", "LUM", "THY1"],
    "Epithelial cells": ["EPCAM", "KRT8", "KRT18", "KRT19"],
    "Cycling/Proliferating cells": ["MKI67", "TOP2A", "CDK1", "PCNA"],
    "Erythroid cells": ["HBB", "HBA1", "HBA2", "ALAS2"],
}


def _normalize_genes(genes: Iterable[str]) -> List[str]:
    return [str(g).strip().upper() for g in genes if str(g).strip()]


def _score_cell_types(genes: List[str]) -> List[tuple[str, int]]:
    gene_set = set(genes)
    scored: List[tuple[str, int]] = []
    for cell_type, hints in CELL_TYPE_HINTS.items():
        score = sum(1 for g in hints if g.upper() in gene_set)
        if score > 0:
            scored.append((cell_type, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def _format_cluster_interpretation(cluster: str, genes: List[str]) -> str:
    top_genes = genes[:8]
    scores = _score_cell_types(genes)
    if not scores:
        return (
            f"- Cluster {cluster}: markers {', '.join(top_genes) if top_genes else 'N/A'}; "
            "no strong canonical match detected. Suggest manual review and tissue-context validation."
        )
    best = scores[0]
    alternatives = ", ".join([ct for ct, _ in scores[1:3]]) if len(scores) > 1 else "none"
    confidence = "high" if best[1] >= 3 else "moderate" if best[1] == 2 else "low"
    return (
        f"- Cluster {cluster}: markers {', '.join(top_genes)}; "
        f"suggested cell type: {best[0]} (confidence: {confidence}). "
        f"Alternative possibilities: {alternatives}."
    )


def _compose_interpretation(markers: Dict[str, List[str]]) -> str:
    lines: List[str] = [
        "Cluster Interpretation Summary",
        "This is a rule-based interpretation using canonical marker overlap.",
        "Use it as decision support and confirm with dataset context and orthogonal evidence.",
        "",
    ]
    for cluster, genes in markers.items():
        norm = _normalize_genes(genes or [])
        lines.append(_format_cluster_interpretation(str(cluster), norm))
    lines.append("")
    lines.append("Recommended next step: validate top suggested labels with differential expression and pathway context.")
    return "\n".join(lines)


def _call_llm_provider(_: Dict[str, List[str]]) -> str:
    """Placeholder for future LLM integration."""
    raise NotImplementedError("LLM provider is not configured.")


def interpret_clusters(markers: dict) -> str:
    """
    Interpret cluster marker genes and suggest biological cell types.

    Parameters
    ----------
    markers:
        Mapping of cluster ID -> list of marker genes.

    Returns
    -------
    str
        Human-readable interpretation text.
    """
    if not isinstance(markers, dict) or not markers:
        return "No marker data provided for interpretation."
    # Current default: deterministic local rules; can switch to LLM provider later.
    return _compose_interpretation({str(k): list(v or []) for k, v in markers.items()})

