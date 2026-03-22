import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from core.pipeline import get_ranked_genes_df, run_differential_expression
from utils.styles import inject_global_css, page_header, render_sidebar, render_nav_buttons, show_guidance, PALETTE, PLOTLY_TEMPLATE

st.set_page_config(page_title="Differential Expression", layout="wide")
inject_global_css()
render_sidebar()

page_header(
    "📈", "Differential Expression & Marker Gene Detection",
    "Rank genes that best distinguish each cluster or cell type"
)
show_guidance("de_analysis")

adata = st.session_state.get("adata")
if adata is None:
    st.warning("⚠️ Please upload a dataset first (Step 1).")
    st.stop()
if "leiden" not in adata.obs.columns:
    st.warning("⚠️ Run clustering (Step 3) first.")
    st.stop()

# ── Parameters ───────────────────────────────────────────────────────────────
with st.expander("⚙️ DE Parameters", expanded=True):
    c1, c2, c3, c4 = st.columns(4)
    groupby_col = c1.selectbox(
        "Compare groups by",
        ["leiden"] + (["cell_type"] if "cell_type" in adata.obs.columns else [])
    )
    method = c2.selectbox("DE method", ["wilcoxon", "t-test", "logreg"],
                          help="Wilcoxon rank-sum is robust and non-parametric (recommended)")
    n_genes = c3.number_input("Top genes per group", value=50, min_value=5, max_value=500)
    selected_group = c4.selectbox(
        "View results for group",
        sorted(adata.obs[groupby_col].unique(), key=lambda x: str(x))
    )

if st.button("▶ Run Differential Expression", type="primary"):
    with st.spinner(f"Computing DE markers using {method} across all groups..."):
        try:
            adata = run_differential_expression(adata, groupby_col=groupby_col, method=method, n_genes=int(n_genes))
            st.session_state["adata"] = adata
            st.session_state.setdefault("pipeline_status", {})["Diff. Expression"] = "done"
            st.success("✅ DE analysis complete! Results shown below.")
        except Exception as e:
            st.error(f"DE failed: {e}")

# ── Results ───────────────────────────────────────────────────────────────────
if "rank_genes_groups" not in adata.uns:
    st.info("Run the analysis above to see differential expression results.")
    st.stop()

try:
    raw_df = get_ranked_genes_df(adata, group=str(selected_group))
except Exception as e:
    st.error(f"Could not retrieve DE results: {e}")
    st.stop()

# ── Clean & rename columns ───────────────────────────────────────────────────
COLUMN_RENAME = {
    "names":         "Gene Symbol",
    "scores":        "DE Score",
    "pvals":         "P-value",
    "pvals_adj":     "Adj. P-value (BH)",
    "logfoldchanges":"Log2 Fold Change",
    "group":         "Group",
}
raw_df = raw_df.rename(columns={k: v for k, v in COLUMN_RENAME.items() if k in raw_df.columns})

# Sort by score, add rank
display_df = raw_df.sort_values("DE Score", ascending=False).reset_index(drop=True)
display_df.insert(0, "Rank", range(1, len(display_df) + 1))

# Significance flag
if "Adj. P-value (BH)" in display_df.columns:
    display_df["Significant"] = display_df["Adj. P-value (BH)"].apply(
        lambda p: "✅" if p < 0.05 else "❌"
    )

top_n = int(n_genes)

st.divider()
st.markdown(f"### Results — Group: **{selected_group}**")

# ── Summary metrics ──────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Genes Tested", f"{len(display_df):,}")
if "Adj. P-value (BH)" in display_df.columns:
    sig_count = (display_df["Adj. P-value (BH)"] < 0.05).sum()
    m2.metric("Significant (adj.p<0.05)", f"{sig_count:,}")
if "Log2 Fold Change" in display_df.columns:
    up = (display_df["Log2 Fold Change"] > 0).sum()
    down = (display_df["Log2 Fold Change"] < 0).sum()
    m3.metric("Upregulated", f"{up:,}")
    m4.metric("Downregulated", f"{down:,}")

# ── Table + Bar chart ────────────────────────────────────────────────────────
col_tbl, col_bar = st.columns([3, 2])

with col_tbl:
    st.markdown("#### Top Marker Genes")
    # Format numeric columns
    fmt_df = display_df.head(top_n).copy()
    for col in ["DE Score", "Log2 Fold Change"]:
        if col in fmt_df.columns:
            fmt_df[col] = fmt_df[col].round(4)
    for col in ["P-value", "Adj. P-value (BH)"]:
        if col in fmt_df.columns:
            fmt_df[col] = fmt_df[col].apply(lambda x: f"{x:.2e}")
    st.dataframe(fmt_df, use_container_width=True, height=450)

with col_bar:
    top20 = display_df.head(20)
    if "Log2 Fold Change" in top20.columns:
        top20 = top20.copy()
        top20["Direction"] = top20["Log2 Fold Change"].apply(
            lambda x: "Up" if x >= 0 else "Down"
        )
        fig = px.bar(
            top20, x="Log2 Fold Change", y="Gene Symbol", orientation="h",
            color="Direction",
            color_discrete_map={"Up": "#51CF66", "Down": "#FF6B6B"},
            title=f"Top 20 DE Genes — Group {selected_group}",
            template=PLOTLY_TEMPLATE,
        )
    else:
        fig = px.bar(
            top20, x="DE Score", y="Gene Symbol", orientation="h",
            color="DE Score", color_continuous_scale="Viridis",
            title=f"Top 20 DE Genes — Group {selected_group}",
            template=PLOTLY_TEMPLATE,
        )
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        paper_bgcolor="#0E1117", plot_bgcolor="#161B22", height=450
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Volcano plot ─────────────────────────────────────────────────────────────
if "Log2 Fold Change" in display_df.columns and "Adj. P-value (BH)" in display_df.columns:
    st.markdown("#### 🌋 Volcano Plot")
    vol_df = display_df.copy()
    vol_df["-log10(adj.p)"] = -np.log10(vol_df["Adj. P-value (BH)"].clip(lower=1e-300))
    vol_df["Category"] = "Non-significant"
    vol_df.loc[(vol_df["Adj. P-value (BH)"] < 0.05) & (vol_df["Log2 Fold Change"] > 0.5), "Category"] = "Up (sig.)"
    vol_df.loc[(vol_df["Adj. P-value (BH)"] < 0.05) & (vol_df["Log2 Fold Change"] < -0.5), "Category"] = "Down (sig.)"

    # label top genes
    top_labels = vol_df.nlargest(10, "DE Score")

    fig_v = px.scatter(
        vol_df, x="Log2 Fold Change", y="-log10(adj.p)",
        color="Category",
        color_discrete_map={
            "Up (sig.)": "#51CF66",
            "Down (sig.)": "#FF6B6B",
            "Non-significant": "#555C66"
        },
        hover_data=["Gene Symbol"],
        title=f"Volcano Plot — Group {selected_group}",
        template=PLOTLY_TEMPLATE,
    )
    # Add gene labels
    for _, row in top_labels.iterrows():
        fig_v.add_annotation(
            x=row["Log2 Fold Change"], y=row["-log10(adj.p)"],
            text=row["Gene Symbol"], showarrow=True, arrowhead=2,
            arrowcolor="#8B949E", font=dict(size=9, color="#E6EDF3"),
            bgcolor="rgba(22,27,34,0.8)", borderpad=2,
        )
    fig_v.add_hline(y=-np.log10(0.05), line_dash="dash", line_color="#FFD43B",
                    annotation_text="adj.p=0.05")
    fig_v.add_vline(x=0.5, line_dash="dash", line_color="#8B949E")
    fig_v.add_vline(x=-0.5, line_dash="dash", line_color="#8B949E")
    fig_v.update_layout(paper_bgcolor="#0E1117", plot_bgcolor="#161B22", height=500)
    fig_v.update_traces(marker=dict(size=4, opacity=0.7))
    st.plotly_chart(fig_v, use_container_width=True)

# ── Store for pipeline & download ────────────────────────────────────────────
st.session_state["de_genes"] = display_df["Gene Symbol"].tolist()
st.session_state["de_group"] = selected_group

st.divider()
export_df = display_df.copy()
# Remove helper columns not useful for export
export_df = export_df.drop(columns=["Significant"], errors="ignore")

# ── Export as Excel (.xlsx) so column headers display correctly in Excel ────
import io as _io
xlsx_buf = _io.BytesIO()
with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
    export_df.to_excel(writer, index=False, sheet_name=f"DE_Group_{selected_group}")
    # Auto-size columns
    ws = writer.sheets[f"DE_Group_{selected_group}"]
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)
xlsx_bytes = xlsx_buf.getvalue()

col_dl1, col_dl2 = st.columns(2)
col_dl1.download_button(
    "⬇️ Download DE Results (.xlsx)",
    data=xlsx_bytes,
    file_name=f"DE_markers_{groupby_col}_{selected_group}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="primary",
)
# Also keep CSV as fallback
csv_bytes = export_df.to_csv(index=False).encode("utf-8")
col_dl2.download_button(
    "⬇️ Download DE Results (.csv)",
    data=csv_bytes,
    file_name=f"DE_markers_{groupby_col}_{selected_group}.csv",
    mime="text/csv",
)

render_nav_buttons(7)
