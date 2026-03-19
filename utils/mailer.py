import os
import smtplib
from email.message import EmailMessage


def _cfg(key: str, default: str = ""):
    env_val = os.getenv(key, "").strip()
    if env_val:
        return env_val
    try:
        import streamlit as st

        secrets_val = str(st.secrets.get(key, "")).strip()
        if secrets_val:
            return secrets_val
    except Exception:
        pass
    try:
        from utils.backend_db import get_system_setting

        return get_system_setting(f"mail.{key.lower()}", default)
    except Exception:
        return default


def mail_enabled():
    required = ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM_EMAIL"]
    return all(_cfg(k) for k in required)


def _smtp_client():
    host = _cfg("SMTP_HOST")
    port = int(_cfg("SMTP_PORT", "587"))
    use_ssl = _cfg("SMTP_USE_SSL", "false").strip().lower() == "true"
    use_starttls = _cfg("SMTP_USE_STARTTLS", "true").strip().lower() == "true"
    username = _cfg("SMTP_USERNAME")
    password = _cfg("SMTP_PASSWORD")
    if use_ssl:
        client = smtplib.SMTP_SSL(host, port, timeout=20)
    else:
        client = smtplib.SMTP(host, port, timeout=20)
        if use_starttls:
            client.starttls()
    client.login(username, password)
    return client


def send_email(to_email: str, subject: str, text_body: str):
    if not (to_email or "").strip():
        return False, "Recipient email is required."
    if not mail_enabled():
        return False, "SMTP is not configured."
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = _cfg("SMTP_FROM_EMAIL")
    msg["To"] = (to_email or "").strip().lower()
    msg.set_content(text_body)
    try:
        with _smtp_client() as client:
            client.send_message(msg)
        return True, None
    except Exception as exc:
        return False, str(exc)


def get_mail_diagnostics():
    host = _cfg("SMTP_HOST")
    port = _cfg("SMTP_PORT", "587")
    username = _cfg("SMTP_USERNAME")
    from_email = _cfg("SMTP_FROM_EMAIL")
    password = _cfg("SMTP_PASSWORD")
    use_ssl = _cfg("SMTP_USE_SSL", "false").strip().lower() == "true"
    use_starttls = _cfg("SMTP_USE_STARTTLS", "true").strip().lower() == "true"
    app_public_url = _cfg("APP_PUBLIC_URL", "")
    return {
        "enabled": all([host, port, username, password, from_email]),
        "missing_fields": [
            name
            for name, val in (
                ("SMTP_HOST", host),
                ("SMTP_PORT", port),
                ("SMTP_USERNAME", username),
                ("SMTP_PASSWORD", password),
                ("SMTP_FROM_EMAIL", from_email),
            )
            if not val
        ],
        "host": host,
        "port": port,
        "username_set": bool(username),
        "password_set": bool(password),
        "from_email": from_email,
        "use_ssl": use_ssl,
        "use_starttls": use_starttls,
        "app_public_url": app_public_url,
    }


def _public_base_url():
    return _cfg("APP_PUBLIC_URL", "").strip().rstrip("/")


def send_verification_email(to_email: str, username: str, token: str):
    base = _public_base_url()
    verify_url = f"{base}?verify_user={username}&verify_token={token}" if base else ""
    body = (
        f"Hello {username},\n\n"
        "Welcome to the SingleCell Explorer platform.\n"
        "Use the verification token below to verify your email:\n\n"
        f"{token}\n\n"
        + (f"Quick verification link:\n{verify_url}\n\n" if verify_url else "")
        + "If you did not create this account, ignore this email."
    )
    return send_email(to_email, "Verify your SingleCell Explorer account", body)


def send_password_reset_email(to_email: str, username: str, token: str):
    base = _public_base_url()
    reset_url = f"{base}?reset_email={to_email}&reset_token={token}" if base else ""
    body = (
        f"Hello {username},\n\n"
        "A password reset was requested for your SingleCell Explorer account.\n"
        "Use the reset token below to set a new password:\n\n"
        f"{token}\n\n"
        + (f"Quick reset link:\n{reset_url}\n\n" if reset_url else "")
        + "If you did not request this, you can ignore this email."
    )
    return send_email(to_email, "Reset your SingleCell Explorer password", body)
