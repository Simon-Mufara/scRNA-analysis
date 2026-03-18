APP_TITLE = "SingleCell Clinical & Research Explorer"
APP_ICON = ":material/biotech:"
APP_VERSION = "1.0.0"

# Pipeline step definitions (order matters)
PIPELINE_STEPS = {
    "Upload": "📂",
    "QC": "🔬",
    "Clustering": "📊",
    "Annotation": "🏷️",
    "Gene Explorer": "🔍",
    "Diff. Expression": "📈",
    "Pathway": "🧪",
    "Report": "📄",
}

# QC thresholds
QC_MIN_GENES = 200
QC_MAX_GENES = 5000
QC_MIN_CELLS = 3
QC_MAX_MITO_PCT = 20.0

# Clustering defaults
N_TOP_GENES = 2000
N_PCS = 40
N_NEIGHBORS = 15
LEIDEN_RESOLUTION = 0.5

# Marker genes for clinical reference
CLINICAL_MARKERS = {
    "T cells": ["CD3D", "CD3E", "CD8A", "CD4"],
    "B cells": ["CD19", "MS4A1", "CD79A"],
    "NK cells": ["GNLY", "NKG7", "KLRD1"],
    "Monocytes": ["CD14", "LYZ", "CST3"],
    "Dendritic cells": ["FCER1A", "CST3"],
    "Tumor markers": ["TP53", "BRCA1", "EGFR", "MKI67"],
    "Immune checkpoints": ["PDCD1", "CD274", "CTLA4", "FOXP3"],
}

# CellTypist model default
CELLTYPIST_MODEL = "Immune_All_Low.pkl"

# Pathway gene sets
PATHWAY_GENE_SETS = [
    "KEGG_2021_Human",
    "Reactome_2022",
    "GO_Biological_Process_2023",
    "MSigDB_Hallmark_2020",
]
