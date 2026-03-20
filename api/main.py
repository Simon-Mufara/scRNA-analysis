from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from services.pipeline_service import (
    annotate_celltypist_dataset,
    annotate_marker_dataset,
    cluster_dataset,
    load_adata,
    pathway_from_genes,
    qc_dataset,
    save_adata,
)

app = FastAPI(title="scRNA Explorer API", version="1.0.0")


class DatasetIO(BaseModel):
    input_path: str
    output_path: str


class QCRequest(DatasetIO):
    min_genes: int = 200
    max_genes: int = 5000
    min_cells: int = 3
    max_mito: float = 20.0
    remove_doublets: bool = False


class ClusterRequest(DatasetIO):
    n_top_genes: int = 2000
    n_pcs: int = 40
    n_neighbors: int = 15
    resolution: float = 0.5
    integration_method: str = "none"
    batch_key: str = ""


class MarkerAnnotRequest(DatasetIO):
    score_threshold: float = 0.0


class CellTypistAnnotRequest(DatasetIO):
    model_name: str = "Immune_All_Low.pkl"
    majority_voting: bool = True


class PathwayRequest(BaseModel):
    genes: List[str] = Field(default_factory=list)
    top_n: int = 20
    gene_sets: str = "KEGG_2021_Human"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/pipeline/qc")
def run_qc_endpoint(req: QCRequest):
    try:
        adata = load_adata(req.input_path)
        out = qc_dataset(
            adata,
            min_genes=req.min_genes,
            max_genes=req.max_genes,
            min_cells=req.min_cells,
            max_mito=req.max_mito,
            remove_doublets=req.remove_doublets,
        )
        save_adata(out, req.output_path)
        return {"ok": True, "output_path": req.output_path, "n_obs": int(out.n_obs), "n_vars": int(out.n_vars)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/pipeline/cluster")
def run_cluster_endpoint(req: ClusterRequest):
    try:
        adata = load_adata(req.input_path)
        out = cluster_dataset(
            adata,
            n_top_genes=req.n_top_genes,
            n_pcs=req.n_pcs,
            n_neighbors=req.n_neighbors,
            resolution=req.resolution,
            integration_method=req.integration_method,
            batch_key=req.batch_key,
        )
        save_adata(out, req.output_path)
        return {"ok": True, "output_path": req.output_path, "n_obs": int(out.n_obs), "n_vars": int(out.n_vars)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/pipeline/annotate/marker")
def run_marker_annotation_endpoint(req: MarkerAnnotRequest):
    try:
        adata = load_adata(req.input_path)
        out = annotate_marker_dataset(adata, score_threshold=req.score_threshold)
        save_adata(out, req.output_path)
        return {"ok": True, "output_path": req.output_path}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/pipeline/annotate/celltypist")
def run_celltypist_annotation_endpoint(req: CellTypistAnnotRequest):
    try:
        adata = load_adata(req.input_path)
        out = annotate_celltypist_dataset(adata, model_name=req.model_name, majority_voting=req.majority_voting)
        save_adata(out, req.output_path)
        return {"ok": True, "output_path": req.output_path}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/pipeline/pathway")
def run_pathway_endpoint(req: PathwayRequest):
    try:
        df = pathway_from_genes(req.genes, top_n=req.top_n, gene_sets=req.gene_sets)
        return {"ok": True, "rows": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

