#!/usr/bin/env python
"""Full end-to-end test simulating user workflow"""

import numpy as np
import pandas as pd
from anndata import AnnData

print("=" * 70)
print("SIMULATING FULL USER WORKFLOW")
print("=" * 70)

# Step 1: Create and upload data
print("\n[1/4] Creating test dataset (simulating upload)...")
np.random.seed(42)
X = np.random.poisson(5, size=(400, 2000)).astype(np.float32)
adata = AnnData(X=X)
adata.var_names = [f"Gene_{i:04d}" for i in range(2000)]
adata.obs_names = [f"Cell_{i:03d}" for i in range(400)]
print(f"✓ Created: {adata.shape}")

# Step 2: Run QC
print("\n[2/4] Running Quality Control...")
try:
    from core.qc import compute_qc_metrics, run_qc_filter

    adata = compute_qc_metrics(adata)
    print(f"✓ QC metrics computed")

    adata_qc = run_qc_filter(
        adata,
        min_genes=200,
        max_genes=2500,
        min_cells=3,
        max_mito=20.0,
        remove_doublets=False,
    )
    print(f"✓ QC filter applied: {adata_qc.shape}")
except Exception as e:
    print(f"✗ QC failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 3: Run clustering
print("\n[3/4] Running Clustering...")
try:
    from core.clustering import run_clustering_step

    adata_clust = run_clustering_step(
        adata_qc,
        n_top_genes=2000,
        n_pcs=40,
        n_neighbors=15,
        resolution=0.5,
        integration_method="none",
        batch_key="",
    )
    print(f"✓ Clustering complete: {adata_clust.obs['leiden'].nunique()} clusters")
except Exception as e:
    print(f"✗ Clustering failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 4: Interpret clusters
print("\n[4/4] Interpreting Clusters...")
try:
    from utils.interpretation import interpret_clusters

    interpretations = interpret_clusters(adata_clust, "leiden")
    print(f"✓ Generated {len(interpretations)} cluster interpretations")
    for cid, interp in list(interpretations.items())[:2]:
        print(f"   Cluster {cid}: {interp[:60]}...")
except Exception as e:
    print(f"✗ Interpretation failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "=" * 70)
print("✓ ALL STEPS SUCCESSFUL!")
print("=" * 70)
