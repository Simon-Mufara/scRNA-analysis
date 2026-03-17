# scRNA-analysis

[![Live App](https://img.shields.io/badge/Live%20App-Open%20on%20Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://scrna-analysis.streamlit.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Domain](https://img.shields.io/badge/Domain-scRNA--seq%20Analytics-0A9396)](https://scrna-analysis.streamlit.app)

Clinical and research-focused web application for end-to-end single-cell RNA-seq analysis, built to convert complex molecular data into interpretable biological and translational insights.

## Live Platform

- Application: https://scrna-analysis.streamlit.app
- Repository: Simon-Mufara/scRNA-analysis
- Current status: deployed and active

## What Problem This App Solves

Single-cell datasets are information-rich but often difficult to analyze consistently across teams. Many projects struggle with fragmented workflows, limited reproducibility, and reporting formats that are hard to communicate to non-computational stakeholders.

scRNA-analysis solves this by providing one guided platform that standardizes the full workflow from upload to report generation.

## What The App Does

The platform delivers a complete 8-stage analysis experience:

1. Data upload and validation for .h5ad and .loom files.
2. Quality control and filtering.
3. Clustering and UMAP visualization.
4. Cell type annotation.
5. Gene-level expression exploration.
6. Differential expression analysis.
7. Pathway enrichment analysis.
8. Clinical-style report generation with PDF export.

## Key Capabilities

- Handles large single-cell datasets with a guided interface.
- Tracks analysis progression across stages.
- Generates publication-ready visual and tabular outputs.
- Supports marker-informed and model-assisted annotation workflows.
- Produces structured PDF reports for meetings and collaborations.

## Outputs Available To Users

- QC summaries and filtering diagnostics.
- UMAP and cluster-level visualizations.
- Cell type composition outputs.
- Differential expression marker tables.
- Pathway enrichment summaries.
- Clinical summary report (PDF).

## Who This Is For

- Faculty research groups.
- Clinical and translational research teams.
- Postgraduate students and trainees.
- Bioinformatics-supported wet-lab projects.

## User Guide (PDF)

- In app: Open User Guide from the home page, then click Download User Guide (PDF).
- Direct file in repository: [docs/SingleCell_Explorer_User_Guide.pdf](docs/SingleCell_Explorer_User_Guide.pdf)

## Partnership Value

- Standardized and reproducible analysis practice across projects.
- Faster transition from raw data to interpretable results.
- Better communication of findings to multidisciplinary audiences.
- Training-friendly environment for onboarding new users.

## Technology

- Streamlit
- Scanpy and AnnData
- Plotly
- CellTypist
- GSEApy
- FPDF2

## License

MIT License. See [LICENSE](LICENSE).
