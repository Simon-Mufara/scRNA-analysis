import importlib
import sys


def main():
    required = ["fastapi", "scanpy", "numpy"]
    failures = []

    for pkg in required:
        try:
            importlib.import_module(pkg)
        except Exception as exc:
            failures.append((pkg, str(exc)))

    if failures:
        for pkg, err in failures:
            print(f"[ERROR] Failed to import {pkg}: {err}")
        sys.exit(1)

    print("[OK] Environment validation successful: fastapi, scanpy, numpy imports are working.")


if __name__ == "__main__":
    main()
