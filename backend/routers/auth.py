from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from utils.backend_db import (
    authenticate_user_account,
    assign_user_to_team,
    ensure_team,
    get_conn,
    get_user_by_email,
    get_user_by_username,
    hash_password,
    init_db,
    issue_password_reset_token_ttl,
    reset_password_with_token_only,
)
from utils.mailer import mail_enabled, send_password_reset_link_email

router = APIRouter(tags=["auth"])


class SignupPayload(BaseModel):
    username: str
    email: str
    password: str
    team_name: str = ""


class LoginPayload(BaseModel):
    username: str
    password: str
    login_mode: str = "Individual"
    team_name: str = ""


class RequestPasswordResetPayload(BaseModel):
    email: str


class ResetPasswordPayload(BaseModel):
    token: str
    new_password: str


@dataclass
class SignupUserRecord:
    username: str
    email: str
    hashed_password: str
    role: str
    email_verified: int = 1
    created_at: str = ""
    id: int | None = None


class SQLiteUserSession:
    def __init__(self):
        self.conn = get_conn()

    def add(self, user: SignupUserRecord):
        cursor = self.conn.execute(
            """
            INSERT INTO users (username, email, email_verified, role, password_hash, hashed_password, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user.username,
                user.email,
                user.email_verified,
                user.role,
                user.hashed_password,
                user.hashed_password,
                user.created_at,
            ),
        )
        user.id = cursor.lastrowid

    def commit(self):
        self.conn.commit()

    def refresh(self, user: SignupUserRecord):
        row = self.conn.execute(
            "SELECT id, email, hashed_password, created_at FROM users WHERE username = ? LIMIT 1",
            (user.username,),
        ).fetchone()
        if row:
            user.id = row["id"]
            user.email = row["email"]
            user.hashed_password = row["hashed_password"]
            user.created_at = row["created_at"]

    def close(self):
        self.conn.close()


@router.post("/signup")
def signup(payload: SignupPayload):
    init_db()
    username = (payload.username or "").strip().lower()
    email = (payload.email or "").strip().lower()
    password = payload.password or ""
    team_name = (payload.team_name or "").strip()
    if not username:
        return {"status": "error", "data": None, "error": "Username is required."}
    if len(password) < 8:
        return {"status": "error", "data": None, "error": "Password must be at least 8 characters."}
    if not email or "@" not in email:
        return {"status": "error", "data": None, "error": "Valid email is required."}
    if get_user_by_username(username):
        return {"status": "error", "data": None, "error": "Username already exists."}
    if get_user_by_email(email):
        return {"status": "error", "data": None, "error": "Email is already linked to another account."}

    user = SignupUserRecord(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        role="team" if team_name else "individual",
        created_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
    db = SQLiteUserSession()
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except sqlite3.IntegrityError:
        return {"status": "error", "data": None, "error": "Username or email already exists."}
    finally:
        db.close()

    if team_name:
        ensure_team(team_name)
        assign_user_to_team(username=user.username, team_name=team_name, is_admin=False)

    stored_user = get_user_by_email(user.email)
    if not stored_user:
        return {"status": "error", "data": None, "error": "Failed to persist user."}
    return {"status": "success", "data": {"message": "Account created successfully.", "email": stored_user["email"]}, "error": None}


@router.post("/login")
def login(payload: LoginPayload):
    user, err = authenticate_user_account(payload.username, payload.password, payload.login_mode, payload.team_name)
    if not user:
        return {"status": "error", "data": None, "error": err or "Invalid email or password."}
    return {"status": "success", "data": user, "error": None}


@router.post("/request-password-reset")
def request_password_reset(payload: RequestPasswordResetPayload):
    email = (payload.email or "").strip().lower()
    if not email:
        return {"status": "error", "data": None, "error": "Email is required."}
    user = get_user_by_email(email)
    if user:
        token, err = issue_password_reset_token_ttl(email, ttl_seconds=900)
        if token and mail_enabled():
            sent, mail_err = send_password_reset_link_email(user["email"], user["username"], token)
            if not sent:
                return {"status": "error", "data": None, "error": mail_err or "Failed to send reset email."}
        elif err:
            return {"status": "error", "data": None, "error": err}
    return {"status": "success", "data": {"message": "If the email exists, a reset link has been sent."}, "error": None}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordPayload):
    ok, err = reset_password_with_token_only(payload.token, payload.new_password)
    if not ok:
        return {"status": "error", "data": None, "error": err or "Invalid or expired reset token."}
    return {"status": "success", "data": {"message": "Password reset successful."}, "error": None}
