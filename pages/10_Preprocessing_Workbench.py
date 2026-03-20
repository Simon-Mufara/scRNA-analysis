import os
import tempfile
from pathlib import Path

import pandas as pd
import scanpy as sc
import streamlit as st

from utils.styles import inject_global_css, page_header, render_sidebar

st.set_page_config(page_title="Preprocessing Workbench", layout="wide")
inject_global_css()
render_sidebar()

page_header(
    "🧰",
    "Preprocessing Workbench",
    "Plan and run pre-analysis steps: FASTQ intake, alignment command templates, conversion to .h5ad/.loom, and file validation",
)

st.info(
    "This module helps users complete pre-analysis tasks in one place. "
    "Sequencing/alignment execution still requires server-side tools (Cell Ranger/STARsolo)."
)

tab_fastq, tab_align, tab_convert, tab_validate = st.tabs(
    ["📥 FASTQ Intake", "🧬 Alignment Builder", "🔄 Convert to AnnData/Loom", "✅ Validate Prepared File"]
)

with tab_fastq:
    st.markdown("### Raw data intake")
    st.caption("Upload FASTQ files for tracking and checklist completion before alignment.")
    fastqs = st.file_uploader(
        "Upload FASTQ/FASTQ.GZ files",
        type=["fastq", "fq", "gz"],
        accept_multiple_files=True,
        help="For large datasets, place files on server storage and use server paths in Alignment Builder.",
    )
    run_id = st.text_input("Run / batch ID", placeholder="e.g. RUN_2026_03_20_A")
    platform = st.selectbox("Sequencing platform", ["Illumina", "MGI", "Other"])
    if fastqs:
        rows = []
        for f in fastqs:
            rows.append({"file": f.name, "size_mb": round(f.size / (1024 ** 2), 2)})
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    checklist = {
        "FASTQ naming convention checked": st.checkbox("FASTQ naming convention checked"),
        "Sample sheet available": st.checkbox("Sample sheet available"),
        "Reference genome decided": st.checkbox("Reference genome decided"),
    }
    if all(checklist.values()):
        st.success(f"FASTQ intake ready for alignment{f' ({run_id})' if run_id else ''} on {platform}.")

with tab_align:
    st.markdown("### Alignment + count matrix command templates")
    engine = st.selectbox("Alignment engine", ["Cell Ranger", "STARsolo"])
    sample_id = st.text_input("Sample ID", placeholder="sample_001")
    ref_path = st.text_input("Reference path", placeholder="/refs/refdata-gex-GRCh38-2024-A")
    fastq_path = st.text_input("FASTQ path", placeholder="/data/fastq/")
    out_path = st.text_input("Output path", placeholder="/data/alignment_out/")

    cmd = ""
    if engine == "Cell Ranger":
        cmd = (
            f"cellranger count --id={sample_id or 'sample_001'} "
            f"--transcriptome={ref_path or '/refs/GRCh38'} "
            f"--fastqs={fastq_path or '/data/fastq'} "
            f"--sample={sample_id or 'sample_001'} "
            f"--localcores=16 --localmem=64"
        )
    else:
        cmd = (
            "STAR --runThreadN 16 --genomeDir "
            f"{ref_path or '/refs/star_index'} "
            f"--readFilesIn {fastq_path or '/data/fastq/R1.fastq.gz'} {fastq_path or '/data/fastq/R2.fastq.gz'} "
            "--readFilesCommand zcat "
            "--soloType CB_UMI_Simple --soloFeatures Gene "
            f"--outFileNamePrefix {(out_path or '/data/alignment_out/')}"
        )
    st.code(cmd, language="bash")
    st.download_button(
        "⬇️ Download command script",
        data=(cmd + "\n").encode("utf-8"),
        file_name=f"{engine.lower().replace(' ', '_')}_command.sh",
        mime="text/x-shellscript",
    )

with tab_convert:
    st.markdown("### Convert matrix/metadata to .h5ad (and optional .loom)")
    input_mode = st.selectbox("Input mode", ["10x matrix directory", "CSV matrix file", "Existing .h5ad"])
    source_path = st.text_input("Source path on server", placeholder="/data/project/sample_outs/filtered_feature_bc_matrix")
    output_path = st.text_input("Output .h5ad path", placeholder="/data/project/sample_processed.h5ad")
    make_loom = st.checkbox("Also export .loom")
    if st.button("▶ Convert and save", type="primary", key="convert_prep"):
        try:
            if not source_path.strip():
                st.error("Source path is required.")
            elif not output_path.strip():
                st.error("Output path is required.")
            else:
                if input_mode == "10x matrix directory":
                    adata = sc.read_10x_mtx(source_path, var_names="gene_symbols")
                elif input_mode == "CSV matrix file":
                    adata = sc.read_csv(source_path).T
                else:
                    adata = sc.read_h5ad(source_path)
                adata.write_h5ad(output_path)
                msg = f"✅ Saved .h5ad: {output_path} ({adata.n_obs:,} cells × {adata.n_vars:,} genes)"
                if make_loom:
                    loom_path = str(Path(output_path).with_suffix(".loom"))
                    adata.write_loom(loom_path)
                    msg += f"\n✅ Saved .loom: {loom_path}"
                st.success(msg)
        except Exception as e:
            st.error(f"Conversion failed: {e}")

with tab_validate:
    st.markdown("### Validate prepared file consistency")
    val_path = st.text_input("Prepared file path (.h5ad/.loom)", placeholder="/data/project/sample_processed.h5ad")
    if st.button("▶ Validate file", key="validate_prepared"):
        try:
            if not val_path.strip():
                st.error("Path is required.")
            else:
                suffix = Path(val_path).suffix.lower()
                if suffix == ".loom":
                    adata = sc.read_loom(val_path)
                else:
                    adata = sc.read_h5ad(val_path)
                checks = {
                    "Cells > 0": adata.n_obs > 0,
                    "Genes > 0": adata.n_vars > 0,
                    "Unique cell IDs": adata.obs_names.is_unique,
                    "Unique gene IDs": adata.var_names.is_unique,
                    "No missing obs column names": not adata.obs.columns.isnull().any(),
                    "No missing var column names": not adata.var.columns.isnull().any(),
                }
                rows = [{"check": k, "status": "PASS" if v else "FAIL"} for k, v in checks.items()]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                if all(checks.values()):
                    st.success("Prepared file is consistent and ready for Upload Data step.")
                else:
                    st.warning("Some checks failed. Resolve issues before downstream analysis.")
                st.caption(f"Detected shape: {adata.n_obs:,} cells × {adata.n_vars:,} genes.")
        except Exception as e:
            st.error(f"Validation failed: {e}")

st.divider()
if st.button("➡️ Continue to Upload Data", type="primary"):
    st.switch_page("pages/1_Upload_Data.py")
