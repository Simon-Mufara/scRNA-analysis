# scRNA-analysis

Clinical and research-focused Streamlit platform for end-to-end single-cell RNA-seq analysis.

## Live App

Target Streamlit app URL (repo-name style):

**https://scrna-analysis.streamlit.app**

Note: Streamlit subdomains are lowercase, so `scRNA-analysis` becomes `scrna-analysis`.

## Features

- Upload and process large `.h5ad` / `.loom` datasets
- Quality control (cell/gene filters, mitochondrial content)
- Clustering and UMAP visualization
- Cell type annotation (marker scoring, CellTypist, manual mapping)
- Differential expression analysis
- Pathway enrichment analysis
- Clinical report generation (PDF)

## Project Structure

```text
app.py
config.py
requirements.txt
.streamlit/config.toml
pages/
utils/
models/
data/
```

## Local Run

### 1) Create environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2) Start Streamlit

```bash
streamlit run app.py
```

Default local URL:

- http://localhost:8501

## Deploy on Streamlit Community Cloud

### App configuration

- Repository: `Simon-Mufara/scRNA-analysis`
- Branch: `main`
- Main file path: `app.py`
- App URL/subdomain: `scrna-analysis` (closest valid match to repo name)

### Steps

1. Go to Streamlit Community Cloud and sign in with GitHub.
2. Click **Create app**.
3. Select repo `Simon-Mufara/scRNA-analysis`.
4. Set **Main file path** to `app.py`.
5. Set custom app URL to `scrna-analysis`.
6. Click **Deploy**.

When deployment completes, your app link will be:

**https://scrna-analysis.streamlit.app**

## Recommended Production Notes

- Keep `.streamlit/config.toml` tracked for consistent server/theme behavior.
- For very large datasets, use server-side paths when possible.
- Ensure enough RAM and temporary disk space for large file uploads.

## Tech Stack

- Streamlit
- Scanpy / AnnData
- Plotly
- CellTypist
- GSEApy

## License

Add your preferred license (MIT, Apache-2.0, etc.) in a `LICENSE` file.
