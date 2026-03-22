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


def run_gsea_prerank(ranked_genes: pd.DataFrame, gene_sets: str = "KEGG_2021_Human", top_n: int = 20) -> pd.DataFrame:
    """Run pre-ranked GSEA (fgsea-like workflow) using gseapy.prerank."""
    if ranked_genes is None or ranked_genes.empty:
        return pd.DataFrame()
    required = {"gene", "score"}
    if not required.issubset(set(ranked_genes.columns)):
        return pd.DataFrame()
    prerank_input = ranked_genes[["gene", "score"]].copy()
    prerank_input = prerank_input.dropna().drop_duplicates(subset=["gene"])
    if prerank_input.empty:
        return pd.DataFrame()
    pre_res = gp.prerank(
        rnk=prerank_input,
        gene_sets=gene_sets,
        outdir=None,
        seed=42,
        min_size=10,
        max_size=500,
        permutation_num=100,
        verbose=False,
    )
    if pre_res is None or getattr(pre_res, "res2d", None) is None:
        return pd.DataFrame()
    out = pre_res.res2d.reset_index(drop=False)
    # Handle both 'index' and existing 'Term' column cases
    if "index" in out.columns and "Term" not in out.columns:
        out = out.rename(columns={"index": "Term"})
    elif "index" in out.columns:
        out = out.drop("index", axis=1)
    # Remove duplicate column occurrences (keep first)
    out = out.loc[:, ~out.columns.duplicated(keep='first')]
    if "FDR q-val" in out.columns:
        out = out.sort_values("FDR q-val", ascending=True)
    return out.head(top_n)
