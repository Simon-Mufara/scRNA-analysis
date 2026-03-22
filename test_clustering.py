#!/usr/bin/env python
"""Test clustering pipeline directly"""

import scanpy as sc
import numpy as np
from utils.clustering import run_clustering

# Create a small test dataset
print("Creating test dataset...")
X = np.random.poisson(5, size=(300, 2000))  # 300 cells, 2000 genes
adata = sc.AnnData(X=X)
adata.var_names = [f"Gene_{i}" for i in range(2000)]
adata.obs_names = [f"Cell_{i}" for i in range(300)]

print(f"Test dataset: {adata.shape}")
print(f"X type: {type(adata.X)}")

try:
    print("\nRunning clustering pipeline...")
    adata = run_clustering(
        adata,
        n_top_genes=2000,
        n_pcs=40,
        n_neighbors=15,
        resolution=0.5,
        integration_method="none",
        batch_key="",
    )
    print("✅ Clustering succeeded!")
    print(f"Clusters found: {adata.obs['leiden'].nunique()}")
    print(f"UMAP coords: {'X_umap' in adata.obsm}")
except Exception as e:
    print(f"❌ Clustering failed: {e}")
    import traceback
    traceback.print_exc()
