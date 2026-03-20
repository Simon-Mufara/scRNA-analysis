from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_analyze_endpoint_returns_200_with_expected_json(monkeypatch, tmp_path: Path):
    in_file = tmp_path / "sample.h5ad"
    in_file.write_bytes(b"dummy")

    def _fake_start_analysis(_: str):
        return "job-123"

    monkeypatch.setattr("backend.routers.jobs.start_analysis", _fake_start_analysis)

    resp = client.post("/analyze", json={"input_path": str(in_file)})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "success"
    assert payload["error"] is None
    assert "data" in payload
    assert payload["data"]["job_id"] == "job-123"
    assert payload["data"]["status"] == "queued"


def test_results_endpoint_returns_200_with_expected_json(monkeypatch):
    def _fake_results(_job_id: str):
        return {
            "job_id": "job-123",
            "status": "completed",
            "output_path": "/tmp/out_analyzed.h5ad",
            "n_obs": 100,
            "n_vars": 50,
            "umap_coordinates": [[0.1, 0.2], [0.3, 0.4]],
            "cluster_labels": ["0", "1"],
        }

    monkeypatch.setattr("backend.routers.jobs.get_analysis_results", _fake_results)

    resp = client.get("/results/job-123")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "success"
    assert payload["error"] is None
    assert "data" in payload
    assert payload["data"]["job_id"] == "job-123"
    assert payload["data"]["status"] == "completed"
    assert isinstance(payload["data"]["umap_coordinates"], list)
    assert isinstance(payload["data"]["cluster_labels"], list)


def test_status_endpoint_returns_200_with_expected_json(monkeypatch):
    monkeypatch.setattr(
        "backend.routers.jobs.get_analysis_status",
        lambda _job_id: {"job_id": "job-123", "status": "queued", "progress": 0, "error": None},
    )

    resp = client.get("/status/job-123")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "success"
    assert payload["error"] is None
    assert "data" in payload
    assert payload["data"]["job_id"] == "job-123"
    assert payload["data"]["status"] == "queued"
    assert payload["data"]["progress"] == 0
