import secrets
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app
import utils.backend_db as backend_db

client = TestClient(app)


def _unique_user():
    suffix = secrets.token_hex(4)
    return f"apitest_{suffix}", f"apitest_{suffix}@example.com", "strongpass123"


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(backend_db, "DB_PATH", tmp_path / "platform_backend_test.db")
    backend_db.init_db()


def test_auth_signup_login_reset_flow(monkeypatch):
    username, email, password = _unique_user()
    token_store = {"value": ""}

    def _fake_send_reset(to_email: str, username_arg: str, token: str):
        assert to_email == email
        assert username_arg == username
        token_store["value"] = token
        return True, None

    monkeypatch.setattr("backend.routers.auth.mail_enabled", lambda: True)
    monkeypatch.setattr("backend.routers.auth.send_password_reset_link_email", _fake_send_reset)

    signup_resp = client.post(
        "/signup",
        json={"username": username, "email": email, "password": password, "team_name": ""},
    )
    assert signup_resp.status_code == 200
    signup_payload = signup_resp.json()
    assert signup_payload["status"] == "success"
    assert signup_payload["error"] is None

    login_resp = client.post(
        "/login",
        json={"username": email, "password": password, "login_mode": "Individual", "team_name": ""},
    )
    assert login_resp.status_code == 200
    login_payload = login_resp.json()
    assert login_payload["status"] == "success"
    assert login_payload["error"] is None
    assert login_payload["data"]["username"] == username

    reset_request_resp = client.post("/request-password-reset", json={"email": email})
    assert reset_request_resp.status_code == 200
    reset_request_payload = reset_request_resp.json()
    assert reset_request_payload["status"] == "success"
    assert reset_request_payload["error"] is None
    assert token_store["value"]

    reset_resp = client.post("/reset-password", json={"token": token_store["value"], "new_password": "newpass123"})
    assert reset_resp.status_code == 200
    reset_payload = reset_resp.json()
    assert reset_payload["status"] == "success"
    assert reset_payload["error"] is None

    relogin_resp = client.post(
        "/login",
        json={"username": username, "password": "newpass123", "login_mode": "Individual", "team_name": ""},
    )
    assert relogin_resp.status_code == 200
    relogin_payload = relogin_resp.json()
    assert relogin_payload["status"] == "success"
    assert relogin_payload["error"] is None


def test_auth_error_handling(monkeypatch):
    bad_signup = client.post(
        "/signup",
        json={"username": "baduser", "email": "invalid-email", "password": "short", "team_name": ""},
    )
    assert bad_signup.status_code == 200
    bad_signup_payload = bad_signup.json()
    assert bad_signup_payload["status"] == "error"
    assert bad_signup_payload["error"]

    bad_login = client.post(
        "/login",
        json={"username": "missing@example.com", "password": "wrongpass123", "login_mode": "Individual", "team_name": ""},
    )
    assert bad_login.status_code == 200
    bad_login_payload = bad_login.json()
    assert bad_login_payload["status"] == "error"
    assert bad_login_payload["error"]

    empty_reset = client.post("/request-password-reset", json={"email": ""})
    assert empty_reset.status_code == 200
    empty_reset_payload = empty_reset.json()
    assert empty_reset_payload["status"] == "error"
    assert "Email is required" in (empty_reset_payload["error"] or "")

    monkeypatch.setattr(
        "backend.routers.auth.reset_password_with_token_only",
        lambda token, new_password: (False, "Invalid or expired reset token."),
    )
    bad_reset = client.post("/reset-password", json={"token": "bad-token", "new_password": "newpass123"})
    assert bad_reset.status_code == 200
    bad_reset_payload = bad_reset.json()
    assert bad_reset_payload["status"] == "error"
    assert bad_reset_payload["error"]
