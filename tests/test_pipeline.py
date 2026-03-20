from pathlib import Path

import numpy as np
import pandas as pd
from anndata import AnnData

from core.pipeline import run_pipeline


def test_run_pipeline_smoke(tmp_path: Path):
    n_cells, n_genes = 300, 80
    x = np.random.poisson(1.5, size=(n_cells, n_genes)).astype(float)
    obs = pd.DataFrame(index=[f"cell_{i}" for i in range(n_cells)])
    var_names = [f"gene_{i}" for i in range(n_genes - 2)] + ["MT-CO1", "MT-ND1"]
    var = pd.DataFrame(index=var_names)
    adata = AnnData(X=x, obs=obs, var=var)
    in_path = tmp_path / "input.h5ad"
    adata.write_h5ad(in_path)

    out = run_pipeline(str(in_path))

    assert isinstance(out, AnnData)
    assert out.n_obs > 0
    assert out.n_vars > 0
    assert "X_umap" in out.obsm
    assert "leiden" in out.obs.columns
