from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from utils.backend_db import (
    authenticate_user_account,
    get_user_by_email,
    issue_password_reset_token_ttl,
    register_user_account,
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


@router.post("/signup")
def signup(payload: SignupPayload):
    ok, err = register_user_account(payload.username, payload.password, payload.email, payload.team_name)
    if not ok:
        return {"status": "error", "data": None, "error": err or "Unable to create account."}
    return {"status": "success", "data": {"message": "Account created successfully."}, "error": None}


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
