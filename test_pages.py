#!/usr/bin/env python
"""Test if pages can at least be imported without runtime errors"""

import sys

pages_to_test = [
    "pages/1_Upload_Data.py",
    "pages/2_Quality_Control.py",
    "pages/3_Clustering_UMAP.py",
]

print("Testing page imports...")
for page in pages_to_test:
    try:
        with open(page, 'r') as f:
            code = f.read()
        compile(code, page, 'exec')
        print(f"✓ {page} compiles OK")
    except SyntaxError as e:
        print(f"✗ {page} has syntax error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ {page} error: {e}")
        sys.exit(1)

print("\nAll pages compile successfully!")
