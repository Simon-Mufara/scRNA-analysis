from datetime import datetime
from typing import Optional

import streamlit as st

from config import APP_TITLE, APP_VERSION
from utils.styles import inject_global_css, page_header, render_sidebar


st.set_page_config(page_title="User Guide", layout="wide")
inject_global_css()
render_sidebar()


def build_user_guide_pdf() -> Optional[bytes]:
    try:
        from fpdf import FPDF
    except ImportError:
        return None

    font_family = "Helvetica"

    class GuidePDF(FPDF):
        def header(self):
            self.set_fill_color(13, 17, 23)
            self.rect(0, 0, 210, 24, "F")
            self.set_font(font_family, "B", 11)
            self.set_text_color(0, 212, 255)
            self.set_xy(10, 7)
            self.cell(0, 6, f"{APP_TITLE} - User Guide")
            self.set_font(font_family, "", 8)
            self.set_text_color(139, 148, 158)
            self.set_xy(10, 14)
            self.cell(0, 5, f"Version {APP_VERSION} | Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")

        def footer(self):
            self.set_y(-12)
            self.set_font(font_family, "", 7)
            self.set_text_color(100, 110, 120)
            self.cell(0, 5, f"Page {self.page_no()} | SingleCell Clinical and Research Explorer", align="C")

    pdf = GuidePDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()
    pdf.set_margins(14, 28, 14)

    def heading(text: str):
        pdf.set_fill_color(20, 24, 32)
        pdf.set_text_color(0, 212, 255)
        pdf.set_font(font_family, "B", 11)
        pdf.cell(0, 8, text, ln=True, fill=True)
        pdf.ln(1)

    def body(text: str):
        pdf.set_text_color(22, 27, 34)
        pdf.set_font(font_family, "", 10)
        pdf.multi_cell(0, 6, text)
        pdf.ln(1)

    heading("Purpose")
    body(
        "This guide explains how to use the SingleCell Clinical and Research Explorer "
        "for complete scRNA-seq analysis, from data upload to report export."
    )

    heading("Recommended Workflow")
    body(
        "1) Upload Data: Load .h5ad or .loom data from browser or server path.\n"
        "2) Quality Control: Apply filters and inspect QC distributions.\n"
        "3) Clustering and UMAP: Run dimensionality reduction and cluster detection.\n"
        "4) Cell Type Annotation: Assign biological labels to clusters.\n"
        "5) Gene Explorer: Investigate marker expression across groups.\n"
        "6) Differential Expression: Identify statistically informative genes.\n"
        "7) Pathway Analysis: Interpret biology through enrichment outputs.\n"
        "8) Clinical Report: Compile findings and export PDF summary."
    )

    heading("Input and Output Expectations")
    body(
        "Inputs: AnnData-compatible files, optional metadata annotations, and marker gene context.\n"
        "Outputs: UMAPs, cluster summaries, marker tables, pathway enrichments, and PDF reports."
    )

    heading("Result Interpretation Checklist")
    body(
        "- Confirm QC metrics are within acceptable ranges for your tissue type.\n"
        "- Validate cluster stability and biological plausibility.\n"
        "- Cross-check annotation labels with canonical markers.\n"
        "- Prioritize differential genes by effect size and relevance.\n"
        "- Interpret pathways in the context of the study design and phenotype."
    )

    heading("Good Practice for Reporting")
    body(
        "Include project metadata, cohort details, and assumptions in every report. "
        "Clearly separate exploratory findings from clinically actionable conclusions."
    )

    heading("Disclaimer")
    body(
        "This platform supports research and translational analysis workflows. "
        "It is not a standalone diagnostic system and should not replace clinical judgment."
    )

    raw_pdf = pdf.output(dest="S")
    if isinstance(raw_pdf, str):
        return raw_pdf.encode("latin-1", "replace")
    if isinstance(raw_pdf, (bytes, bytearray)):
        return bytes(raw_pdf)
    return None


page_header(
    "📘",
    "User Guide and Training Manual",
    "Step-by-step instructions for using the platform and interpreting results",
)

st.markdown(
    """
<div style="background:rgba(22,27,34,0.7);border:1px solid #21262D;border-radius:14px;padding:16px 20px;margin-bottom:14px;">
  <div style="color:#E6EDF3;font-size:1rem;font-weight:700;margin-bottom:6px;">Who this guide is for</div>
  <div style="color:#8B949E;font-size:0.9rem;line-height:1.6;">
    Researchers, clinical trainees, postgraduate students, and faculty collaborators who need a consistent
    process for single-cell RNA-seq analysis and reporting.
  </div>
</div>
""",
    unsafe_allow_html=True,
)

left, right = st.columns([2, 1])

with left:
    st.markdown("### Standard User Journey")
    st.markdown(
        """
1. Open the platform and go to **Upload Data**.
2. Load your data file and verify cell and gene counts.
3. Run **Quality Control** and set filtering thresholds.
4. Run **Clustering and UMAP** to reveal structure.
5. Use **Cell Type Annotation** to assign identities.
6. Use **Gene Explorer** to inspect expression patterns.
7. Run **Differential Expression** and **Pathway Analysis**.
8. Finalize findings in **Clinical Report** and export PDF.
"""
    )

    st.markdown("### Interpreting Results")
    st.markdown(
        """
- Check quality metrics before interpreting biology.
- Confirm annotation labels using marker genes.
- Use differential expression together with pathway analysis for stronger conclusions.
- Record assumptions and limitations in your final report notes.
"""
    )
    with st.expander("Before Upload: How to prepare .h5ad/.loom input files", expanded=False):
        st.markdown(
            """
            If you do not yet have `.h5ad` or `.loom`, complete these preparation steps first:
            1. Raw data generation (FASTQ from sequencing instrument)
            2. Alignment + count matrix generation (e.g., Cell Ranger/STARsolo)
            3. Basic QC and filtering in your preferred preprocessing tool
            4. Convert matrix + metadata to AnnData/loom format
            5. Validate that genes, cells, and metadata columns are consistent

            This app starts at the analysis stage and expects a prepared file.
            """
        )
    with st.expander("Alternative tool options by pipeline stage", expanded=False):
        st.markdown(
            """
            - QC: Scanpy QC metrics, Scrublet (doublets), custom thresholds
            - Clustering: Leiden/Louvain alternatives depending on study design
            - Annotation: marker-based scoring + CellTypist + manual label curation
            - Pathways: Enrichr sets, Reactome/GO alternatives, rank-based enrichment
            """
        )

with right:
    st.markdown("### Download Manual")
    pdf_bytes = build_user_guide_pdf()
    if pdf_bytes is None:
        st.warning("PDF export dependency is missing. Install fpdf2 to enable manual download.")
    else:
        st.download_button(
            label="Download User Guide (PDF)",
            data=pdf_bytes,
            file_name="SingleCell_Explorer_User_Guide.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )

    st.markdown(
        """
<div style="margin-top:12px;background:rgba(0,212,255,0.06);border:1px solid rgba(0,212,255,0.25);border-radius:12px;padding:12px 14px;">
  <div style="color:#00D4FF;font-size:0.8rem;font-weight:700;letter-spacing:0.04em;">MEETING-READY TIP</div>
  <div style="color:#8B949E;font-size:0.85rem;line-height:1.55;margin-top:4px;">
    Share this PDF with evaluators before live demonstrations so they can follow each analysis stage.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
