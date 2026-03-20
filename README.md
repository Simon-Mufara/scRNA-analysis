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

## Optional FastAPI Backend

The Streamlit app remains fully functional.  
For API-based execution, run:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Available minimal endpoints:
- `GET /health`
- `POST /pipeline/qc`
- `POST /pipeline/cluster`
- `POST /pipeline/annotate/marker`
- `POST /pipeline/annotate/celltypist`
- `POST /pipeline/pathway`

## ilifu HPC + SLURM Deployment (Recommended for large workloads)

Use this pattern on ilifu:
- Run **Streamlit** and **FastAPI** as lightweight services.
- Run heavy analysis on compute nodes via **SLURM jobs**.
- Keep uploads/results on shared storage.

### 1) Environment setup on ilifu

```bash
git clone https://github.com/Simon-Mufara/scRNA-analysis.git
cd scRNA-analysis
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p logs data/uploads
```

Set required environment variables (example):

```bash
export FRONTEND_URL="https://your-public-app-url"
export SUPPORT_EMAIL="support@your-org.org"
export SMTP_HOST="..."
export SMTP_PORT="587"
export SMTP_USERNAME="..."
export SMTP_PASSWORD="..."
export SMTP_FROM_EMAIL="..."
```

### 2) Start web services

```bash
sbatch scripts/hpc/start_backend.sbatch
sbatch scripts/hpc/start_streamlit.sbatch
```

### 3) Run compute through SLURM

Enable SLURM execution in backend:

```bash
export ANALYSIS_RUNNER=slurm
export SLURM_RESULTS_DIR=/scratch3/users/simon/scRNA-analysis/data/slurm_results
```

When users call `POST /analyze`, backend now submits `sbatch` automatically and tracks job status/results.

Manual submit (optional):

```bash
sbatch scripts/hpc/run_pipeline.sbatch /shared/path/to/input.h5ad /scratch3/users/simon/scRNA-analysis/data/slurm_results/manual.json
```

### 4) ilifu login-node workflow (no disruption to other users)

SSH login:

```bash
ssh simon@slurm.ilifu.ac.za
cd /scratch3/users/simon
git clone https://github.com/Simon-Mufara/scRNA-analysis.git
cd scRNA-analysis
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
mkdir -p logs data/uploads data/slurm_results
```

Run everything via scheduler (preferred):

```bash
sbatch scripts/hpc/start_backend.sbatch
sbatch scripts/hpc/start_streamlit.sbatch
squeue -u simon
```

### 5) Production routing

- Put Nginx/Apache in front of Streamlit/FastAPI for HTTPS and stable URLs.
- Restrict direct node ports; expose only proxy endpoints.
- Keep debug endpoints for internal use only.

## Extended Bioinformatics Options

For teams needing additional or alternative workflows, this platform aligns with common ecosystems:

- **R ecosystem:** Seurat, Azimuth, SingleR, DoubletFinder, harmony.
- **Python ecosystem:** scverse/Scanpy, scVI-tools, BBKNN, Scanorama, decoupler.
- **Pathway/enrichment alternatives:** fgsea, clusterProfiler, ReactomePA.

Use these options for method cross-checking, reproducibility audits, and institution-specific SOPs.

## Security and Authentication

- Production authenticator: Microsoft Entra ID (OIDC + MFA).
- Configure these environment variables before launch:
  - `ENTRA_TENANT_ID`
  - `ENTRA_CLIENT_ID`
  - `ENTRA_CLIENT_SECRET`
  - `ENTRA_REDIRECT_URI`
  - `ENTRA_ADMIN_GROUP_ID` (optional, for organization admin role)
  - `ENTRA_TEAM_GROUP_MAP` (optional JSON map of group-id to team name)
- Configure SMTP for professional account verification and password reset emails:
  - `SMTP_HOST`
  - `SMTP_PORT` (e.g., `587`)
  - `SMTP_USERNAME`
  - `SMTP_PASSWORD`
  - `SMTP_FROM_EMAIL`
  - `SMTP_USE_SSL` (`true` or `false`)
  - `FRONTEND_URL` (recommended; used to embed full frontend links like `/verify?token=...`)
  - `APP_PUBLIC_URL` (optional fallback for legacy setups)
- Local demo login remains available for development/testing only.
- Demo users are restricted to the embedded PBMC example dataset; custom uploads require a created account or Entra sign-in.

## License

MIT License. See [LICENSE](LICENSE).
