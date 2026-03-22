import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

from core.pipeline import build_prerank_input
from utils.pathway import get_top_pathways, run_gsea_prerank
from utils.styles import inject_global_css, page_header, render_sidebar, render_nav_buttons, show_guidance, PLOTLY_TEMPLATE
from utils.interpretation import show_explanation_button, interpret_pathway_results
from utils.export import export_to_excel, export_to_csv
from config import PATHWAY_GENE_SETS

st.set_page_config(page_title="Pathway Analysis", layout="wide")
inject_global_css()
render_sidebar()
adata = st.session_state.get("adata")

page_header(
    "🧪", "Pathway Enrichment Analysis",
    "Identify enriched biological pathways using Enrichr (KEGG, Reactome, GO, Hallmark)"
)
show_guidance("pathways")


def show_pathway_results(df: pd.DataFrame):
    display_cols = [c for c in ["Term", "Adjusted P-value", "Overlap", "Combined Score", "Genes"]
                    if c in df.columns]
    sig_df = df[df["Adjusted P-value"] < 0.05] if "Adjusted P-value" in df.columns else df

    m1, m2, m3 = st.columns(3)
    m1.metric("Pathways tested", len(df))
    m2.metric("Significant (adj.p<0.05)", len(sig_df))
    top_term = df.iloc[0]["Term"] if "Term" in df.columns and len(df) else "—"
    m3.metric("Top pathway", top_term[:35] + "..." if len(top_term) > 35 else top_term)

    st.markdown("#### 📊 Top Enriched Pathways")
    st.dataframe(df[display_cols].head(30), use_container_width=True, height=350)

    if "Term" in df.columns and "Combined Score" in df.columns and len(df) > 0:
        top = df.head(20).copy()
        top["-log10(adj.p)"] = -np.log10(top["Adjusted P-value"].clip(lower=1e-300))
        fig = px.bar(
            top, x="Combined Score", y="Term", orientation="h",
            color="-log10(adj.p)", color_continuous_scale="Plasma",
            title="Top 20 Enriched Pathways",
            template=PLOTLY_TEMPLATE,
            labels={"-log10(adj.p)": "-log₁₀(adj.p)"},
        )
        fig.update_layout(
            yaxis={"categoryorder": "total ascending"},
            paper_bgcolor="#0E1117", plot_bgcolor="#161B22",
            height=550,
            coloraxis_colorbar=dict(title="-log₁₀(adj.p)"),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Dot plot: -log10 p vs combined score
        if "Overlap" in df.columns:
            top2 = df.head(25).copy()
            try:
                top2["Overlap_n"] = top2["Overlap"].apply(
                    lambda x: int(x.split("/")[0]) if isinstance(x, str) else x
                )
            except Exception:
                top2["Overlap_n"] = 5
            top2["-log10(adj.p)"] = -np.log10(top2["Adjusted P-value"].clip(lower=1e-300))
            fig2 = px.scatter(
                top2, x="Combined Score", y="-log10(adj.p)",
                size="Overlap_n", color="Overlap_n",
                color_continuous_scale="Viridis",
                hover_data=["Term"],
                title="Pathway Significance vs. Enrichment Score",
                template=PLOTLY_TEMPLATE,
            )
            fig2.update_layout(paper_bgcolor="#0E1117", plot_bgcolor="#161B22", height=400)
            st.plotly_chart(fig2, use_container_width=True)

    csv = export_to_csv(df, numeric_cols=None)

    # ── Interpretation ──────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 💡 Interpreting Pathway Results")
    with st.expander("📖 What do these pathways mean?", expanded=False):
        pathway_interpretation = interpret_pathway_results(df, cell_type="")
        st.markdown(pathway_interpretation)

    show_explanation_button("pathway", data=None, button_key="pathway_explain")
    st.divider()

    # ── Export with proper formatting ──────────────────────────────────────────
    numeric_cols = ["Adjusted P-value", "Combined Score"]
    numeric_cols = [col for col in numeric_cols if col in df.columns]

    xlsx_bytes = export_to_excel(
        df,
        sheet_name="Pathway_Results",
        numeric_cols=numeric_cols
    )

    dl1, dl2 = st.columns(2)
    dl1.download_button(
        "⬇️ Download Pathway Results (.xlsx)",
        data=xlsx_bytes,
        file_name="pathway_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
    dl2.download_button("⬇️ Download Pathway Results (.csv)", data=csv,
                        file_name="pathway_results.csv", mime="text/csv")
    st.session_state["pathway_results"] = df


# ── Tabs ──────────────────────────────────────────────────────────────────────
de_genes = st.session_state.get("de_genes", [])
tab_de, tab_custom, tab_compare, tab_prerank = st.tabs([
    "📈 From DE Results", "✏️ Custom Gene List", "⚖️ Compare Libraries", "🏁 Pre-ranked GSEA"
])

with tab_de:
    if not de_genes:
        st.info("Run Differential Expression (Step 6) first, or use the Custom Gene List tab.")
    else:
        group = st.session_state.get("de_group", "?")
        st.success(f"Using **{len(de_genes)}** DE markers from group: **{group}**")
        st.caption("Preview: " + ", ".join(de_genes[:12]) + "...")

        c1, c2 = st.columns(2)
        gene_sets = c1.selectbox("Gene set library", PATHWAY_GENE_SETS, key="de_gs")
        top_n = c2.slider("Max pathways to show", 5, 50, 20, key="de_top")

        if st.button("▶ Run Pathway Analysis", type="primary", key="run_de"):
            with st.spinner("Querying Enrichr..."):
                try:
                    df = get_top_pathways(de_genes, top_n=top_n, gene_sets=gene_sets)
                    if df.empty:
                        st.warning("No significant pathways found (adj.p < 0.05).")
                    else:
                        show_pathway_results(df)
                except Exception as e:
                    st.error(f"Pathway analysis failed: {e}")
                    st.info("Enrichr requires internet access.")

with tab_custom:
    gene_input = st.text_area(
        "Paste gene symbols (comma or newline separated)",
        placeholder="TP53\nBRCA1\nEGFR\nMYC\nCD8A\nFOXP3",
        height=130
    )
    c1, c2 = st.columns(2)
    gene_sets_c = c1.selectbox("Gene set library", PATHWAY_GENE_SETS, key="custom_gs")
    top_n_c = c2.slider("Max pathways", 5, 50, 20, key="custom_top")

    if st.button("▶ Run Pathway Analysis", type="primary", key="run_custom"):
        genes = [g.strip() for line in gene_input.split("\n") for g in line.split(",") if g.strip()]
        if not genes:
            st.warning("Enter at least one gene symbol.")
        else:
            with st.spinner("Querying Enrichr..."):
                try:
                    df = get_top_pathways(genes, top_n=top_n_c, gene_sets=gene_sets_c)
                    if df.empty:
                        st.warning("No significant pathways found.")
                    else:
                        show_pathway_results(df)
                except Exception as e:
                    st.error(f"Failed: {e}")

with tab_compare:
    st.markdown("Compare enrichment across multiple gene set databases simultaneously.")
    comp_genes_input = st.text_area("Gene list for comparison",
                                    value=", ".join(de_genes[:30]) if de_genes else "",
                                    height=80)
    selected_libs = st.multiselect("Libraries to compare", PATHWAY_GENE_SETS,
                                   default=PATHWAY_GENE_SETS[:3])

    if st.button("▶ Compare Libraries", type="primary", key="run_compare"):
        genes = [g.strip() for g in comp_genes_input.replace("\n", ",").split(",") if g.strip()]
        if not genes or not selected_libs:
            st.warning("Provide genes and select at least one library.")
        else:
            results = {}
            for lib in selected_libs:
                with st.spinner(f"Querying {lib}..."):
                    try:
                        df = get_top_pathways(genes, top_n=10, gene_sets=lib)
                        results[lib] = df
                    except Exception:
                        pass

            if results:
                for lib, df in results.items():
                    with st.expander(f"📚 {lib} — {len(df)} significant pathways"):
                        if not df.empty and "Term" in df.columns:
                            st.dataframe(df[["Term", "Adjusted P-value", "Combined Score"]].head(10),
                                         use_container_width=True)

with tab_prerank:
    st.markdown("Run pre-ranked pathway analysis (fgsea-like) using DE rank statistics.")
    if adata is None or "rank_genes_groups" not in adata.uns:
        st.info("Run Differential Expression first to use pre-ranked GSEA.")
    else:
        groups = sorted(adata.obs["leiden"].astype(str).unique().tolist()) if "leiden" in adata.obs.columns else []
        group = st.selectbox("Group for ranking", groups) if groups else st.text_input("Group")
        pr_gene_set = st.selectbox("Gene set library", PATHWAY_GENE_SETS, key="prerank_gs")
        pr_top_n = st.slider("Top pathways", 5, 50, 20, key="prerank_top")
        if st.button("▶ Run Pre-ranked GSEA", type="primary", key="run_prerank"):
            try:
                ranked = build_prerank_input(adata, group=str(group))
                out = run_gsea_prerank(ranked, gene_sets=pr_gene_set, top_n=pr_top_n)
                if out.empty:
                    st.warning("No pathway results returned from prerank.")
                else:
                    display_cols = [c for c in ["Term", "NES", "NOM p-val", "FDR q-val"] if c in out.columns]
                    st.dataframe(out[display_cols] if display_cols else out, use_container_width=True)
            except Exception as e:
                st.error(f"Pre-ranked GSEA failed: {e}")

render_nav_buttons(8)
