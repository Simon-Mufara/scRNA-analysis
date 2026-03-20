from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "success"
    assert payload["error"] is None


def test_analyze_missing_file_returns_404():
    resp = client.post("/analyze", json={"input_path": "/tmp/definitely_missing_12345.h5ad"})
    assert resp.status_code == 404
    payload = resp.json()
    assert payload["status"] == "error"


def test_upload_rejects_invalid_extension(tmp_path: Path):
    bad_file = tmp_path / "bad.txt"
    bad_file.write_text("not supported", encoding="utf-8")
    with bad_file.open("rb") as fh:
        resp = client.post("/upload", files={"file": ("bad.txt", fh, "text/plain")})
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["status"] == "error"

