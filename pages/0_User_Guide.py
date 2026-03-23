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

    heading("Clinical Relevance by Tool")
    body(
        "Upload Data: Confirms the cohort and feature space are correctly loaded before interpretation. "
        "Clinical impact: prevents downstream conclusions from wrong files or incomplete metadata.\n"
        "Quality Control: Removes low-quality cells and technical artifacts (e.g., high mitochondrial fraction). "
        "Clinical impact: improves reliability of detected populations and reduces false biological signals.\n"
        "Clustering and UMAP: Identifies transcriptionally distinct cellular groups and visual separation. "
        "Clinical impact: reveals disease-associated subpopulations and heterogeneity relevant to prognosis/therapy.\n"
        "Cell Type Annotation: Maps clusters to biological identities using marker evidence and model support. "
        "Clinical impact: links molecular clusters to interpretable cell compartments for pathology and immune context.\n"
        "Gene Explorer: Visualizes expression of genes of interest across clusters/cell types. "
        "Clinical impact: supports validation of biomarkers, target expression, and mechanism hypotheses.\n"
        "Differential Expression: Quantifies genes enriched between groups or states. "
        "Clinical impact: prioritizes candidate biomarkers and therapeutic targets with statistical support.\n"
        "Pathway Analysis: Converts gene lists into pathway-level biology (e.g., immune activation, cell-cycle). "
        "Clinical impact: supports mechanistic interpretation and translational narrative building.\n"
        "Clinical Report: Consolidates evidence into a communication-ready summary. "
        "Clinical impact: improves multidisciplinary review, reproducibility, and handoff quality."
    )

    heading("How to Read Each Output")
    body(
        "Quality Control: Use distributions/thresholds to confirm retained cells match expected tissue quality; "
        "investigate aggressive filtering that removes biologically plausible populations.\n"
        "Clustering/UMAP: Treat UMAP distances as neighborhood cues, not absolute lineage distance; "
        "confirm clusters with marker genes before naming.\n"
        "Annotation: Prefer labels supported by multiple canonical markers; mark low-confidence clusters for review.\n"
        "Gene Explorer: Compare both expression intensity and fraction of expressing cells across clusters.\n"
        "Differential Expression: Prioritize genes with strong effect size and corrected significance, then validate externally.\n"
        "Pathway Analysis: Focus on coherent pathway themes across top terms rather than a single enriched term.\n"
        "Report: Separate exploratory findings from clinically actionable statements and document assumptions."
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
    st.markdown("### Clinical Relevance and Interpretation by Module")
    with st.expander("1) Quality Control (QC): why it matters clinically", expanded=False):
        st.markdown(
            """
- Removes noisy or stressed cells that can mislead interpretation.
- Check retained cell counts and mitochondrial trends to avoid over-filtering clinically relevant rare populations.
- Treat QC as reliability control: poor QC can create false biomarker signals.
"""
        )
    with st.expander("2) Clustering and UMAP: how to interpret structure", expanded=False):
        st.markdown(
            """
- Clusters represent transcriptionally similar groups, often corresponding to biologically meaningful subtypes.
- UMAP is for visual neighborhood structure; distance is not a direct quantitative biological distance.
- Clinical use: identify heterogeneity (e.g., resistant subclones, immune states) for downstream review.
"""
        )
    with st.expander("3) Cell Type Annotation: confidence and caveats", expanded=False):
        st.markdown(
            """
- Use annotation as a hypothesis supported by marker genes, not a final truth by itself.
- Highest confidence comes from agreement across marker genes, model outputs, and tissue context.
- Flag ambiguous clusters as mixed/uncertain for expert adjudication.
"""
        )
    with st.expander("4) Gene Explorer: reading expression patterns", expanded=False):
        st.markdown(
            """
- Assess both expression intensity and the proportion of cells expressing each gene.
- Compare across cell types/clusters to validate biomarker specificity.
- Clinical use: support target validation and phenotype characterization.
"""
        )
    with st.expander("5) Differential Expression: prioritizing findings", expanded=False):
        st.markdown(
            """
- Combine adjusted p-values with effect size when prioritizing genes.
- Validate top genes against known biology and orthogonal assays where possible.
- Clinical use: shortlist candidate biomarkers and mechanisms for translational follow-up.
"""
        )
    with st.expander("6) Pathway Analysis: turning genes into mechanisms", expanded=False):
        st.markdown(
            """
- Interpret enriched pathways as biological themes, not isolated proof.
- Look for consistency across related pathways (immune signaling, proliferation, metabolism).
- Clinical use: frame molecular findings into disease-relevant mechanisms and therapeutic hypotheses.
"""
        )
    with st.expander("7) Clinical Report: communication standards", expanded=False):
        st.markdown(
            """
- Summarize methods, thresholds, key findings, and limitations.
- Clearly separate exploratory observations from potentially actionable insights.
- Use this report to support multidisciplinary review, not as a standalone diagnostic decision tool.
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
    with st.expander("Broader bioinformatics ecosystem (equivalent tools)", expanded=False):
        st.markdown(
            """
            Use these tools for cross-validation or team preference alignment:
            - **R / Seurat ecosystem:** Seurat, Azimuth, SingleR, DoubletFinder, harmony.
            - **Python ecosystem:** Scanpy/scverse, scVI-tools, BBKNN, Scanorama, decoupler.
            - **Cell type references:** CellTypist models, curated marker atlases, tissue-specific references.
            - **Pathway/genesets:** gseapy, fgsea, clusterProfiler, ReactomePA.
            - **Interoperability:** Keep `.h5ad` as primary exchange format; export CSV summaries for reviewers.

            Recommended practice: validate major conclusions with at least one independent method
            (e.g., CellTypist + marker-based annotation, or Leiden + Harmony-integrated re-analysis).
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
            width="stretch",
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
