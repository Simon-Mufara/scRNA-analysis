import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
import io
import plotly.express as px
import plotly.graph_objects as go

from utils.styles import inject_global_css, page_header, render_sidebar, render_nav_buttons, PALETTE
from utils.auth import get_current_user
from utils.collaboration import capture_pipeline_training_record, submit_clinical_report

st.set_page_config(page_title="Clinical Report", layout="wide")
inject_global_css()
render_sidebar()
current_user = get_current_user()

_rpt_col, _rpt_img = st.columns([3, 1])
with _rpt_col:
    page_header(
        "📄", "Clinical Summary Report",
        "Auto-compiled research & clinical interpretation report with PDF export"
    )
with _rpt_img:
    st.markdown("""<div style="border-radius:12px;overflow:hidden;border:1px solid #21262D;height:95px;margin-top:4px;">
    <img src="https://images.unsplash.com/photo-1576671081837-49000212a370?w=400&q=80"
        style="width:100%;height:100%;object-fit:cover;opacity:0.65;" alt="clinical report"/>
    </div>""", unsafe_allow_html=True)

adata        = st.session_state.get("adata")
report_date  = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
de_genes     = st.session_state.get("de_genes", [])
de_group     = st.session_state.get("de_group", "N/A")
pathway_df   = st.session_state.get("pathway_results")

if adata is not None:
    n_cells      = adata.n_obs
    n_genes      = adata.n_vars
    n_clusters   = adata.obs["leiden"].nunique()    if "leiden"    in adata.obs else 0
    n_cell_types = adata.obs["cell_type"].nunique() if "cell_type" in adata.obs else 0
    ct_counts    = adata.obs["cell_type"].value_counts() if "cell_type" in adata.obs else pd.Series()
    median_mito  = round(float(adata.obs["pct_counts_mt"].median()), 1) if "pct_counts_mt" in adata.obs.columns else None
    median_genes_per_cell = int(adata.obs["n_genes_by_counts"].median()) if "n_genes_by_counts" in adata.obs else None
else:
    n_cells = n_genes = n_clusters = n_cell_types = 0
    ct_counts = pd.Series()
    median_mito = median_genes_per_cell = None

# ── Analysis completeness ─────────────────────────────────────────────────────
steps_done = {
    "Data Loaded":      adata is not None,
    "QC Performed":     adata is not None and "n_genes_by_counts" in (adata.obs.columns if adata is not None else []),
    "Clustering":       n_clusters > 0,
    "Cell Annotation":  n_cell_types > 0,
    "DE Analysis":      len(de_genes) > 0,
    "Pathway Analysis": pathway_df is not None and not (pathway_df.empty if hasattr(pathway_df, "empty") else False),
}
score = int(sum(steps_done.values()) / len(steps_done) * 100)
required_steps_complete = all(steps_done.values())

# ── Metric bar ────────────────────────────────────────────────────────────────
m_cols = st.columns(6)
metrics = [
    ("Cells",       f"{n_cells:,}",     "#00D4FF"),
    ("Genes",       f"{n_genes:,}",     "#A855F7"),
    ("Clusters",    str(n_clusters),    "#51CF66"),
    ("Cell Types",  str(n_cell_types),  "#FFD43B"),
    ("DE Markers",  str(len(de_genes)), "#FF922B"),
    ("Complete",    f"{score}%",        "#51CF66" if score==100 else "#FFD43B" if score>=50 else "#FF6B6B"),
]
for col, (label, val, color) in zip(m_cols, metrics):
    col.markdown(
        f'<div style="background:rgba(22,27,34,0.6);border:1px solid #21262D;border-top:2px solid {color};'
        f'border-radius:12px;padding:14px 10px;text-align:center;">'
        f'<div style="color:{color};font-size:1.5rem;font-weight:800;letter-spacing:-0.04em;">{val}</div>'
        f'<div style="color:#6E7681;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.08em;margin-top:4px;">{label}</div>'
        f'</div>', unsafe_allow_html=True)

# ── Pipeline checklist ────────────────────────────────────────────────────────
st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
chips = ""
for step, done in steps_done.items():
    if done:
        chips += (f'<span style="background:rgba(81,207,102,0.1);color:#51CF66;border:1px solid rgba(81,207,102,0.3);'
                  f'border-radius:20px;padding:3px 12px;font-size:0.75rem;font-weight:600;margin:2px;display:inline-block;">&#10003; {step}</span>')
    else:
        chips += (f'<span style="background:rgba(110,118,129,0.08);color:#6E7681;border:1px solid #21262D;'
                  f'border-radius:20px;padding:3px 12px;font-size:0.75rem;margin:2px;display:inline-block;">&#9675; {step}</span>')
st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:4px;">{chips}</div>', unsafe_allow_html=True)

# ── Metadata inputs ───────────────────────────────────────────────────────────
st.divider()
st.markdown("### 📝 Report Metadata")
m1, m2, m3 = st.columns(3)
analyst   = m1.text_input("Analyst / Clinician", placeholder="Dr. Smith")
project   = m2.text_input("Project / Sample ID",  placeholder="PBMC_run01")
diagnosis = m3.text_input("Clinical Context",     placeholder="NSCLC biopsy, immunotherapy")
notes = st.text_area(
    "Clinical Interpretation & Recommendations", height=150,
    placeholder=(
        "- Describe key cell populations identified\n"
        "- Note therapeutically relevant findings (T cell exhaustion, tumour markers)\n"
        "- Flag potential biomarkers or checkpoint targets\n"
        "- Recommend follow-up assays or validation steps"
    )
)

# ── Dark HTML report preview ──────────────────────────────────────────────────
st.divider()
st.markdown("### 👁 Interactive Report Preview")

# Build cell population rows
ct_html = ""
if not ct_counts.empty:
    for ct, count in ct_counts.items():
        pct = count / n_cells * 100
        bar = max(1, min(100, int(pct * 2.5)))
        ct_html += (
            '<tr>'
            f'<td style="color:#C9D1D9;font-size:0.82rem;padding:4px 10px 4px 0;white-space:nowrap;">{ct}</td>'
            f'<td style="color:#8B949E;font-size:0.78rem;padding:4px 14px 4px 0;white-space:nowrap;">{count:,}</td>'
            '<td style="padding:4px 0;width:150px;">'
            '<div style="background:#161B22;border-radius:4px;height:7px;">'
            f'<div style="background:linear-gradient(90deg,#00D4FF,#A855F7);height:7px;border-radius:4px;width:{bar}%;"></div>'
            '</div></td>'
            f'<td style="color:#00D4FF;font-size:0.78rem;padding:4px 0 4px 8px;">{pct:.1f}%</td>'
            '</tr>'
        )

# DE gene tags
de_html = '<p style="color:#6E7681;font-size:0.82rem;">No DE analysis performed.</p>'
if de_genes:
    tags = "".join(
        f'<span style="background:rgba(0,212,255,0.08);color:#00D4FF;border:1px solid rgba(0,212,255,0.2);'
        f'border-radius:6px;padding:2px 7px;font-size:0.73rem;margin:2px;display:inline-block;">{g}</span>'
        for g in de_genes[:20]
    )
    extra = f'<span style="color:#6E7681;font-size:0.73rem;"> +{len(de_genes)-20} more</span>' if len(de_genes) > 20 else ""
    de_html = f'<p style="color:#8B949E;font-size:0.8rem;margin:0 0 6px;">Group: <b style="color:#E6EDF3;">{de_group}</b></p><div style="display:flex;flex-wrap:wrap;gap:2px;">{tags}{extra}</div>'

# Pathway rows
pw_html = ""
if pathway_df is not None and not pathway_df.empty and "Term" in pathway_df.columns:
    for i, (_, row) in enumerate(pathway_df.head(8).iterrows()):
        adj_p = row.get("Adjusted P-value", "")
        p_str = f"{float(adj_p):.2e}" if adj_p != "" else "N/A"
        s_val = row.get("Combined Score", "")
        s_str = f"{float(s_val):.1f}" if s_val != "" else "N/A"
        bg = "rgba(0,212,255,0.03)" if i % 2 == 0 else "transparent"
        pw_html += (
            f'<tr style="background:{bg};">'
            f'<td style="color:#C9D1D9;font-size:0.8rem;padding:5px 10px 5px 0;">{str(row["Term"])[:65]}</td>'
            f'<td style="color:#51CF66;font-size:0.78rem;padding:5px 10px;text-align:right;">{p_str}</td>'
            f'<td style="color:#FFD43B;font-size:0.78rem;padding:5px 0;text-align:right;">{s_str}</td>'
            '</tr>'
        )

# QC summary block
qc_html = ""
if median_mito is not None:
    mito_col = "#51CF66" if median_mito < 10 else "#FFD43B" if median_mito < 20 else "#FF6B6B"
    qc_html = (
        '<div style="background:rgba(22,27,34,0.6);border:1px solid #21262D;border-radius:10px;padding:12px 16px;margin-top:10px;">'
        '<div style="color:#6E7681;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;margin-bottom:6px;">QC Summary</div>'
        '<div style="display:flex;gap:24px;flex-wrap:wrap;">'
        f'<div><span style="color:#6E7681;font-size:0.8rem;">Median genes/cell: </span><span style="color:#00D4FF;font-weight:700;">{median_genes_per_cell:,}</span></div>'
        f'<div><span style="color:#6E7681;font-size:0.8rem;">Median mito %: </span><span style="color:{mito_col};font-weight:700;">{median_mito}%</span></div>'
        '</div></div>'
    )

def _sec(title, color):
    return (
        f'<div style="background:linear-gradient(90deg,rgba({color},0.12),transparent);'
        f'border-left:3px solid rgb({color});padding:6px 12px;margin-bottom:10px;border-radius:0 6px 6px 0;">'
        f'<span style="color:rgb({color});font-weight:700;font-size:0.85rem;text-transform:uppercase;letter-spacing:0.06em;">{title}</span>'
        f'</div>'
    )

theme_mode = st.session_state.get("theme_mode", "Dark")
is_light = str(theme_mode).lower() == "light"
report_bg = "#FFFFFF" if is_light else "#0D1117"
report_border = "#D9E2EC" if is_light else "#21262D"
primary_text = "#0F172A" if is_light else "#E6EDF3"
muted_text = "#475569" if is_light else "#8B949E"
section_border = "#CBD5E1" if is_light else "#21262D"
table_text = "#0F172A" if is_light else "#C9D1D9"
section_chip_text = "#0F172A" if is_light else "#C9D1D9"

report_html = (
    f'<div style="background:{report_bg};border:1px solid {report_border};border-radius:16px;padding:28px 32px;font-family:Inter,sans-serif;">'

    # Header
    '<div style="border-bottom:2px solid rgba(0,212,255,0.25);padding-bottom:16px;margin-bottom:22px;">'
    '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">'
    '<div>'
    '<div style="color:#00D4FF;font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;">SingleCell Clinical &amp; Research Explorer SC-CRE v1.0</div>'
    '<div style="color:#E6EDF3;font-size:1.45rem;font-weight:800;letter-spacing:-0.03em;margin:0 0 4px;">Clinical Summary Report</div>'
    f'<div style="color:{muted_text};font-size:0.82rem;">Project: <b style="color:{primary_text};">{project or "N/A"}</b> &nbsp;|&nbsp; Analyst: <b style="color:{primary_text};">{analyst or "N/A"}</b> &nbsp;|&nbsp; Diagnosis: <b style="color:{primary_text};">{diagnosis or "N/A"}</b></div>'
    '</div>'
    f'<div style="text-align:right;"><div style="color:{muted_text};font-size:0.72rem;">Generated</div><div style="color:{primary_text};font-size:0.82rem;font-weight:600;">{report_date}</div></div>'
    '</div></div>'

    # Section 1 – Dataset Summary
    + _sec("1. Dataset Summary", "0,212,255")
    + '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:4px;">'
    + "".join(
        f'<div style="background:rgba({c},0.07);border:1px solid rgba({c},0.18);border-radius:10px;padding:10px 16px;min-width:100px;text-align:center;">'
        f'<div style="color:rgb({c});font-size:1.3rem;font-weight:800;">{v}</div>'
        f'<div style="color:{muted_text};font-size:0.68rem;text-transform:uppercase;letter-spacing:0.08em;margin-top:3px;">{l}</div>'
        f'</div>'
        for l, v, c in [
            ("Cells",      f"{n_cells:,}",  "0,212,255"),
            ("Genes",      f"{n_genes:,}",  "168,85,247"),
            ("Clusters",   str(n_clusters), "81,207,102"),
            ("Cell Types", str(n_cell_types),"255,212,59"),
        ]
    )
    + '</div>'
    + qc_html

    # Section 2 – Cell Populations
    + '<div style="margin-top:18px;"></div>'
    + _sec("2. Cell Population Overview", "168,85,247")
    + ('<table style="width:100%;border-collapse:collapse;color:' + table_text + ';">' + ct_html + '</table>' if ct_html
       else '<p style="color:#6E7681;font-size:0.82rem;">No annotation performed.</p>')

    # Section 3 – DE
    + '<div style="margin-top:18px;"></div>'
    + _sec("3. Differential Expression — Key Markers", "255,146,43")
    + de_html

    # Section 4 – Pathways
    + '<div style="margin-top:18px;"></div>'
    + _sec("4. Pathway Enrichment (Top 8)", "81,207,102")
    + ('<table style="width:100%;border-collapse:collapse;">'
       '<tr>'
       f'<th style="color:{muted_text};font-size:0.68rem;text-transform:uppercase;letter-spacing:0.06em;text-align:left;padding:4px 0;border-bottom:1px solid {section_border};">Pathway Term</th>'
       f'<th style="color:{muted_text};font-size:0.68rem;text-transform:uppercase;text-align:right;padding:4px 10px;border-bottom:1px solid {section_border};">Adj. p-val</th>'
       f'<th style="color:{muted_text};font-size:0.68rem;text-transform:uppercase;text-align:right;padding:4px 0;border-bottom:1px solid {section_border};">Score</th>'
       '</tr>' + pw_html + '</table>'
       if pw_html else '<p style="color:#6E7681;font-size:0.82rem;">No pathway analysis performed.</p>')

    # Section 5 – Interpretation
    + '<div style="margin-top:18px;"></div>'
    + _sec("5. Clinical Interpretation &amp; Recommendations", "116,192,252")
    + f'<p style="color:{section_chip_text};font-size:0.875rem;line-height:1.7;white-space:pre-wrap;">{notes.strip() if notes.strip() else "No clinical notes provided."}</p>'

    # Disclaimer
    + '<div style="background:rgba(255,107,107,0.08);border:1px solid rgba(255,107,107,0.3);border-radius:8px;padding:10px 16px;text-align:center;margin-top:16px;">'
    + '<span style="color:#FF6B6B;font-size:0.78rem;font-weight:700;letter-spacing:0.04em;">&#9888; FOR RESEARCH USE ONLY &mdash; NOT INTENDED FOR CLINICAL DIAGNOSIS OR TREATMENT DECISIONS</span>'
    + '</div>'

    + '</div>'
)
st.markdown(report_html, unsafe_allow_html=True)

# ── Inline charts ─────────────────────────────────────────────────────────────
if not ct_counts.empty or (pathway_df is not None and not pathway_df.empty):
    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
    st.markdown("### 📊 Report Visualisations")
    vc1, vc2 = st.columns(2)

    with vc1:
        if not ct_counts.empty:
            ct_df = ct_counts.reset_index()
            ct_df.columns = ["Cell Type", "Count"]
            fig_ct = px.pie(ct_df, names="Cell Type", values="Count",
                            color_discrete_sequence=PALETTE, hole=0.48,
                            template="plotly_dark", title="Cell Type Composition")
            fig_ct.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                height=340, margin=dict(t=40, b=10, l=10, r=10),
                title_font=dict(size=13, color="#8B949E"),
                legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
            )
            fig_ct.update_traces(textposition="inside", textinfo="percent", textfont_size=11)
            st.plotly_chart(fig_ct, use_container_width=True)

    with vc2:
        if pathway_df is not None and not pathway_df.empty and "Term" in pathway_df.columns and "Combined Score" in pathway_df.columns:
            pw_plot = pathway_df.head(10).copy()
            pw_plot["Short Term"] = pw_plot["Term"].str[:45]
            pw_plot = pw_plot.sort_values("Combined Score", ascending=True)
            fig_pw = px.bar(pw_plot, x="Combined Score", y="Short Term",
                            orientation="h", template="plotly_dark",
                            color="Combined Score",
                            color_continuous_scale=["#00D4FF", "#A855F7", "#FF6B6B"],
                            title="Top Enriched Pathways (Combined Score)")
            fig_pw.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                height=340, margin=dict(t=40, b=10, l=10, r=10),
                title_font=dict(size=13, color="#8B949E"),
                yaxis=dict(tickfont=dict(size=9)),
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig_pw, use_container_width=True)

# ── PDF builder ───────────────────────────────────────────────────────────────
def build_pdf() -> bytes:
    try:
        from fpdf import FPDF
    except ImportError:
        return None
    FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_family = "Helvetica"

    class Report(FPDF):
        def header(self):
            self.set_fill_color(13, 17, 23)
            self.rect(0, 0, 210, 28, "F")
            self.set_font("DV", "B", 11)
            self.set_text_color(0, 212, 255)
            self.set_xy(10, 7)
            self.cell(0, 7, "SingleCell Clinical & Research Explorer (SC-CRE) v1.0")
            self.set_font("DV", "", 8)
            self.set_text_color(139, 148, 158)
            self.set_xy(10, 17)
            self.cell(0, 5, f"Generated: {report_date}  |  Analyst: {analyst or 'N/A'}  |  Project: {project or 'N/A'}")

        def footer(self):
            self.set_y(-12)
            self.set_font("DV", "", 7)
            self.set_text_color(100, 110, 120)
            self.cell(0, 5, f"FOR RESEARCH USE ONLY | Page {self.page_no()} | SC-CRE v1.0.0", align="C")

    pdf = Report(orientation="P", unit="mm", format="A4")
    if os.path.exists(FONT_R) and os.path.exists(FONT_B):
        pdf.add_font("DV", "", FONT_R)
        pdf.add_font("DV", "B", FONT_B)
        font_family = "DV"
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_margins(14, 32, 14)

    def heading(text, rgb=(0, 212, 255)):
        pdf.set_fill_color(20, 24, 32)
        pdf.set_draw_color(*rgb)
        pdf.set_font(font_family, "B", 10)
        pdf.set_text_color(*rgb)
        pdf.cell(0, 7, text, border="B", fill=True, ln=True)
        pdf.ln(2)

    def body(text, size=9):
        pdf.set_font(font_family, "", size)
        pdf.set_text_color(200, 210, 225)
        pdf.multi_cell(0, 5, text)
        pdf.ln(1)

    # Title
    pdf.set_fill_color(16, 20, 28)
    pdf.set_draw_color(0, 212, 255)
    pdf.rect(14, 33, 182, 24, "FD")
    pdf.set_font(font_family, "B", 14)
    pdf.set_text_color(0, 212, 255)
    pdf.set_xy(18, 36)
    pdf.cell(0, 8, "Clinical Summary Report", ln=True)
    pdf.set_font(font_family, "", 8.5)
    pdf.set_text_color(175, 182, 192)
    pdf.set_x(18)
    pdf.cell(0, 5, f"Project: {project or 'N/A'}   |   Diagnosis: {diagnosis or 'N/A'}", ln=True)
    pdf.ln(10)

    # 1. Dataset
    heading("1. Dataset Summary")
    col_w = 44
    for lbl in ["Cells Analysed", "Genes Detected", "Clusters", "Cell Types"]:
        pdf.set_fill_color(22, 27, 34); pdf.set_draw_color(40, 50, 60)
        pdf.set_font(font_family, "", 7); pdf.set_text_color(100, 115, 128)
        pdf.cell(col_w - 1, 5, lbl.upper(), border=1, fill=True, ln=False, align="C")
    pdf.ln(5)
    for val in [f"{n_cells:,}", f"{n_genes:,}", str(n_clusters), str(n_cell_types)]:
        pdf.set_font(font_family, "B", 12); pdf.set_text_color(0, 212, 255)
        pdf.cell(col_w - 1, 8, val, border=1, fill=True, ln=False, align="C")
    pdf.ln(10)
    if median_genes_per_cell:
        body(f"QC: Median genes/cell: {median_genes_per_cell:,}  |  Median mito%: {median_mito or 'N/A'}%")

    # 2. Cell populations
    heading("2. Cell Population Overview", (168, 85, 247))
    if not ct_counts.empty:
        for ct, count in ct_counts.items():
            pct = count / n_cells * 100
            pdf.set_font(font_family, "", 9); pdf.set_text_color(210, 218, 230)
            pdf.cell(70, 5, f"  {ct}", ln=False)
            pdf.cell(22, 5, f"{count:,}", ln=False, align="R")
            bar_w = max(1, min(55, int(pct * 0.75)))
            pdf.set_fill_color(0, 180, 230)
            x, y = pdf.get_x() + 4, pdf.get_y() + 1.5
            pdf.rect(x, y, bar_w, 3, "F")
            pdf.set_xy(x + bar_w + 3, pdf.get_y())
            pdf.set_text_color(0, 212, 255)
            pdf.cell(18, 5, f"{pct:.1f}%", ln=True)
    else:
        body("Not performed.")
    pdf.ln(2)

    # 3. DE
    heading("3. Differential Expression", (255, 146, 43))
    if de_genes:
        body(f"Group: {de_group}")
        body("Top markers: " + ", ".join(de_genes[:20]))
    else:
        body("Not performed.")

    # 4. Pathways
    heading("4. Pathway Enrichment (Top 8)", (81, 207, 102))
    if pathway_df is not None and not pathway_df.empty and "Term" in pathway_df.columns:
        for _, row in pathway_df.head(8).iterrows():
            adj_p = row.get("Adjusted P-value", "")
            p_str = f"{float(adj_p):.2e}" if adj_p != "" else "N/A"
            pdf.set_font(font_family, "", 9); pdf.set_text_color(200, 210, 225)
            pdf.cell(135, 5, f"  {str(row['Term'])[:60]}", ln=False)
            pdf.set_text_color(81, 207, 102)
            pdf.cell(0, 5, f"adj.p={p_str}", ln=True, align="R")
    else:
        body("Not performed.")

    # 5. Interpretation
    heading("5. Clinical Interpretation", (116, 192, 252))
    body(notes.strip() if notes.strip() else "No clinical notes provided.")

    # Disclaimer
    pdf.set_fill_color(30, 15, 15); pdf.set_draw_color(200, 60, 60)
    pdf.rect(14, pdf.get_y() + 2, 182, 11, "FD")
    pdf.set_xy(17, pdf.get_y() + 4)
    pdf.set_font(font_family, "B", 7.5); pdf.set_text_color(235, 90, 90)
    pdf.cell(0, 4, "FOR RESEARCH USE ONLY -- NOT INTENDED FOR CLINICAL DIAGNOSIS OR TREATMENT DECISIONS")

    return bytes(pdf.output())


# ── Exports ───────────────────────────────────────────────────────────────────
st.divider()
st.markdown("### Download Report")

report_lines = [
    "SingleCell Clinical & Research Explorer (SC-CRE) v1.0",
    "Clinical Summary Report",
    f"Generated: {report_date}",
    f"Analyst:   {analyst or 'N/A'}  |  Project: {project or 'N/A'}  |  Diagnosis: {diagnosis or 'N/A'}",
    "", "=" * 60, "1. DATASET SUMMARY", "=" * 60,
    f"  Cells: {n_cells:,}  |  Genes: {n_genes:,}  |  Clusters: {n_clusters}  |  Cell Types: {n_cell_types}",
    "", "=" * 60, "2. CELL POPULATIONS", "=" * 60,
]
for ct, count in ct_counts.items():
    report_lines.append(f"  {ct}: {count:,} cells ({count/n_cells*100:.1f}%)")
report_lines += ["", "=" * 60, "3. DIFFERENTIAL EXPRESSION", "=" * 60]
report_lines.append(f"  Group: {de_group}  Top: {', '.join(de_genes[:20])}" if de_genes else "  Not performed.")
report_lines += ["", "=" * 60, "4. PATHWAY ENRICHMENT", "=" * 60]
if pathway_df is not None and not pathway_df.empty and "Term" in pathway_df.columns:
    for _, row in pathway_df.head(8).iterrows():
        adj_p = row.get("Adjusted P-value", "")
        report_lines.append(f"  {row['Term']}  (adj.p={float(adj_p):.2e})" if adj_p != "" else f"  {row['Term']}")
else:
    report_lines.append("  Not performed.")
report_lines += ["", "=" * 60, "5. CLINICAL INTERPRETATION", "=" * 60,
                 notes.strip() if notes.strip() else "  No notes provided.",
                 "", "=" * 60, "FOR RESEARCH USE ONLY", "=" * 60]
report_text = "\n".join(report_lines)

dl1, dl2, dl3 = st.columns(3)
with dl1:
    st.download_button("📄 Text Report (.txt)", data=report_text.encode(),
        file_name=f"scRNA_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
        mime="text/plain", use_container_width=True)
with dl2:
    pdf_bytes = build_pdf()
    if pdf_bytes:
        st.download_button("📕 PDF Report", data=pdf_bytes,
            file_name=f"scRNA_clinical_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf", type="primary", use_container_width=True)
with dl3:
    if adata is not None and "cell_type" in adata.obs.columns:
        ct_export = adata.obs["cell_type"].value_counts().reset_index()
        ct_export.columns = ["Cell Type", "Cell Count"]
        ct_export["Proportion (%)"] = (ct_export["Cell Count"] / adata.n_obs * 100).round(2)
        st.download_button("📊 Cell Table (.csv)", data=ct_export.to_csv(index=False).encode(),
            file_name="cell_type_summary.csv", mime="text/csv", use_container_width=True)

st.caption("For research use only. Not intended for clinical diagnosis.")

st.divider()
st.markdown("### 🚀 Submit Report")
with st.form("submit_report_form", clear_on_submit=False):
    visibility = st.radio("Visibility", ["Team dashboard", "General dashboard"], horizontal=True)
    submit_report_clicked = st.form_submit_button("Submit report to dashboard", type="primary", use_container_width=True)
if submit_report_clicked:
    user_name = current_user.get("username") or "unknown"
    user_team = current_user.get("team") or "individual"
    report_payload = {
        "project": project or "N/A",
        "analyst": analyst or user_name,
        "diagnosis": diagnosis or "N/A",
        "generated_at": report_date,
        "notes": notes.strip(),
        "metrics": {
            "cells": n_cells,
            "genes": n_genes,
            "clusters": n_clusters,
            "cell_types": n_cell_types,
            "de_genes_count": len(de_genes),
        },
        "filters_used": {
            "de_group": de_group,
            "de_top_genes": de_genes[:20],
            "pathway_terms": pathway_df["Term"].head(10).tolist() if pathway_df is not None and not pathway_df.empty and "Term" in pathway_df.columns else [],
            "pathway_scores": pathway_df["Combined Score"].head(10).tolist() if pathway_df is not None and not pathway_df.empty and "Combined Score" in pathway_df.columns else [],
        },
        "required_steps_complete": required_steps_complete,
        "pipeline_steps": steps_done,
    }
    rec = submit_clinical_report(
        username=user_name,
        team=user_team,
        report_payload=report_payload,
        visibility="public" if visibility == "General dashboard" else "team",
    )
    st.success(f"Report submitted ({rec['visibility']}) and audit logged.")
    capture_pipeline_training_record(user_name, user_team, report_payload)

render_nav_buttons(8)
