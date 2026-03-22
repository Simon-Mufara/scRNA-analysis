#!/usr/bin/env python
"""Debug script to test what happens when running clustering through the full pipeline"""

import sys
import numpy as np
import pandas as pd
from anndata import AnnData

# Test 1: Import all required modules
print("=" * 60)
print("TEST 1: Importing modules...")
print("=" * 60)
try:
    from utils.clustering import run_clustering
    print("✓ utils.clustering imported")
except Exception as e:
    print(f"✗ Failed to import clustering: {e}")
    sys.exit(1)

try:
    from core.clustering import run_clustering_step
    print("✓ core.clustering imported")
except Exception as e:
    print(f"✗ Failed to import run_clustering_step: {e}")
    sys.exit(1)

# Test 2: Create realistic test data
print("\n" + "=" * 60)
print("TEST 2: Creating realistic test data...")
print("=" * 60)

np.random.seed(42)
n_cells = 500
n_genes = 3000

# Create realistic count data (Poisson distributed)
X = np.random.poisson(5, size=(n_cells, n_genes)).astype(np.float32)
adata = AnnData(X=X)
adata.var_names = [f"Gene_{i:04d}" for i in range(n_genes)]
adata.obs_names = [f"Cell_{i:03d}" for i in range(n_cells)]

print(f"✓ Created AnnData: {adata.shape}")
print(f"  - X type: {type(adata.X)}")
print(f"  - X dtype: {adata.X.dtype}")
print(f"  - X range: [{adata.X.min():.2f}, {adata.X.max():.2f}]")

# Test 3: Run clustering with default parameters
print("\n" + "=" * 60)
print("TEST 3: Running clustering (like Streamlit would)...")
print("=" * 60)

try:
    print("Calling run_clustering_step with parameters:")
    print(f"  n_top_genes: 2000")
    print(f"  n_pcs: 40")
    print(f"  n_neighbors: 15")
    print(f"  resolution: 0.5")
    print(f"  integration_method: 'none'")
    print(f"  batch_key: ''")
    print()

    adata = run_clustering_step(
        adata,
        n_top_genes=2000,
        n_pcs=40,
        n_neighbors=15,
        resolution=0.5,
        integration_method="none",
        batch_key="",
    )

    print("✓ Clustering succeeded!")
    print(f"  - Clusters found: {adata.obs['leiden'].nunique()}")
    print(f"  - UMAP in obsm: {'X_umap' in adata.obsm}")
    print(f"  - PCA in obsm: {'X_pca' in adata.obsm}")
    print(f"  - Leiden in obs: {'leiden' in adata.obs}")

    # Show cluster distribution
    print(f"\nCluster distribution:")
    for cluster_id in sorted(adata.obs['leiden'].unique()):
        count = (adata.obs['leiden'] == cluster_id).sum()
        pct = count / adata.n_obs * 100
        print(f"  Cluster {int(cluster_id)}: {count:4d} cells ({pct:5.1f}%)")

except Exception as e:
    print(f"✗ Clustering FAILED: {e}")
    import traceback
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ ALL TESTS PASSED!")
print("=" * 60)
