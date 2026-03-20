import h5py
import pandas as pd
import scanpy as sc


def register_null_reader():
    try:
        from anndata._io.specs.registry import _REGISTRY
        from anndata._io.specs import IOSpec as _IOSpec
        import h5py as _h5py

        _null_spec = _IOSpec("null", "0.1.0")

        @_REGISTRY.register_read(_h5py.Dataset, _null_spec)
        def _read_null_ds(elem):
            return None

        @_REGISTRY.register_read(_h5py.Group, _null_spec)
        def _read_null_grp(elem):
            return None
    except Exception:
        pass


def load_h5ad_safe(path: str):
    register_null_reader()
    try:
        return sc.read_h5ad(path)
    except Exception as e1:
        if "null" not in str(e1).lower() and "IORegistryError" not in str(type(e1).__name__):
            raise

    try:
        adata = sc.read_h5ad(path, backed="r")
        return adata.to_memory()
    except Exception:
        pass

    import anndata as ad
    import scipy.sparse as sp

    def _h5_to_df(grp) -> pd.DataFrame:
        cols = {}
        index = None
        for key in grp.keys():
            val = grp[key]
            if isinstance(val, h5py.Dataset):
                try:
                    arr = val[()]
                    if arr.dtype.kind in ("S", "O"):
                        arr = arr.astype(str)
                    cols[key] = arr
                except Exception:
                    pass
        idx_name = grp.attrs.get("_index", None)
        if idx_name and idx_name in cols:
            index = cols.pop(idx_name)
        elif "_index" in grp:
            raw = grp["_index"][()]
            index = raw.astype(str) if raw.dtype.kind in ("S", "O") else raw
        return pd.DataFrame(cols, index=index)

    with h5py.File(path, "r") as f:
        x_group = f["X"]
        if isinstance(x_group, h5py.Dataset):
            X = x_group[()]
        else:
            data = x_group["data"][()]
            indices = x_group["indices"][()]
            indptr = x_group["indptr"][()]
            shape = tuple(x_group.attrs.get("shape", (len(indptr) - 1, indices.max() + 1)))
            X = sp.csr_matrix((data, indices, indptr), shape=shape)

        obs = _h5_to_df(f["obs"]) if "obs" in f else pd.DataFrame()
        var = _h5_to_df(f["var"]) if "var" in f else pd.DataFrame()

    return ad.AnnData(X=X, obs=obs, var=var)


def load_input_dataset(file_path: str, fmt: str):
    lower_fmt = (fmt or "").lower()
    if ".loom" in lower_fmt:
        return sc.read_loom(file_path)
    if ".csv" in lower_fmt:
        return sc.read_csv(file_path).T
    if ".mtx" in lower_fmt:
        import os

        return sc.read_10x_mtx(os.path.dirname(file_path), var_names="gene_symbols")
    return load_h5ad_safe(file_path)


def load_demo_dataset():
    return sc.datasets.pbmc3k()


def validate_prepared_adata(adata):
    return {
        "Cells > 0": adata.n_obs > 0,
        "Genes > 0": adata.n_vars > 0,
        "Unique cell IDs": adata.obs_names.is_unique,
        "Unique gene IDs": adata.var_names.is_unique,
        "No missing obs column names": not adata.obs.columns.isnull().any(),
        "No missing var column names": not adata.var.columns.isnull().any(),
    }

