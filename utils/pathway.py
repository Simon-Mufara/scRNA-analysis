import gseapy as gp
import pandas as pd
from config import PATHWAY_GENE_SETS


def pathway_analysis(genes: list, gene_sets: str = "KEGG_2021_Human",
                     organism: str = "human") -> pd.DataFrame:
    """Run Enrichr pathway analysis on a gene list."""

    if not genes:
        return pd.DataFrame()

    enr = gp.enrichr(
        gene_list=genes,
        gene_sets=gene_sets,
        organism=organism,
        outdir=None,
    )

    df = enr.results.sort_values("Adjusted P-value")
    return df


def get_top_pathways(genes: list, top_n: int = 20, gene_sets: str = "KEGG_2021_Human") -> pd.DataFrame:
    """Convenience wrapper returning only top significant pathways."""
    df = pathway_analysis(genes, gene_sets=gene_sets)
    if df.empty:
        return df
    return df[df["Adjusted P-value"] < 0.05].head(top_n)
