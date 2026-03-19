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
        # Also support nested secrets blocks, e.g. [mail] smtp_host="..."
        parts = key.lower().split("_", 1)
        if len(parts) == 2:
            section, sub_key = parts
            block = st.secrets.get(section)
            if block:
                nested_val = str(block.get(sub_key, "")).strip()
                if nested_val:
                    return nested_val
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
    timeout = int(_cfg("SMTP_TIMEOUT_SECONDS", "10"))
    if use_ssl:
        client = smtplib.SMTP_SSL(host, port, timeout=timeout)
    else:
        client = smtplib.SMTP(host, port, timeout=timeout)
        if use_starttls:
            client.starttls()
    client.login(username, password)
    return client


def send_email(to_email: str, subject: str, text_body: str, html_body: str = ""):
    if not (to_email or "").strip():
        return False, "Recipient email is required."
    if not mail_enabled():
        return False, "SMTP is not configured."
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = _cfg("SMTP_FROM_EMAIL")
    msg["To"] = (to_email or "").strip().lower()
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")
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
    timeout_seconds = _cfg("SMTP_TIMEOUT_SECONDS", "10")
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
        "timeout_seconds": timeout_seconds,
    }


def _public_base_url():
    return _cfg("APP_PUBLIC_URL", "").strip().rstrip("/")


def send_verification_email(to_email: str, username: str, token: str):
    base = _public_base_url()
    verify_url = f"{base}?verify_user={username}&verify_token={token}" if base else ""
    body = (
        f"Hello {username},\n\n"
        "Welcome to SingleCell Explorer.\n\n"
        "To verify your email, use this one-time verification token:\n"
        f"{token}\n\n"
        + (f"Direct verification link:\n{verify_url}\n\n" if verify_url else "")
        + "For security, this token expires automatically.\n"
        "If you did not create this account, you can safely ignore this message.\n\n"
        "SingleCell Explorer Security Team"
    )
    html = f"""
    <html><body style="font-family:Arial,sans-serif;line-height:1.5;">
      <h3>Verify your SingleCell Explorer account</h3>
      <p>Hello {username},</p>
      <p>Use this one-time verification token:</p>
      <p style="font-size:18px;font-weight:700;">{token}</p>
      {"<p><a href='" + verify_url + "'>Verify my email</a></p>" if verify_url else ""}
      <p>If you did not create this account, you can ignore this email.</p>
      <p>SingleCell Explorer Security Team</p>
    </body></html>
    """
    return send_email(to_email, "Verify your SingleCell Explorer account", body, html)


def send_password_reset_email(to_email: str, username: str, token: str):
    base = _public_base_url()
    reset_url = f"{base}?reset_email={to_email}&reset_token={token}" if base else ""
    body = (
        f"Hello {username},\n\n"
        "We received a password reset request for your SingleCell Explorer account.\n\n"
        "Use this one-time reset token:\n"
        f"{token}\n\n"
        + (f"Direct reset link:\n{reset_url}\n\n" if reset_url else "")
        + "If you did not request this, you can ignore this email.\n\n"
        "SingleCell Explorer Security Team"
    )
    html = f"""
    <html><body style="font-family:Arial,sans-serif;line-height:1.5;">
      <h3>Reset your SingleCell Explorer password</h3>
      <p>Hello {username},</p>
      <p>Use this one-time reset token:</p>
      <p style="font-size:18px;font-weight:700;">{token}</p>
      {"<p><a href='" + reset_url + "'>Reset my password</a></p>" if reset_url else ""}
      <p>If you did not request this, you can ignore this email.</p>
      <p>SingleCell Explorer Security Team</p>
    </body></html>
    """
    return send_email(to_email, "Reset your SingleCell Explorer password", body, html)


def send_username_reminder_email(to_email: str, username: str):
    base = _public_base_url()
    body = (
        "Hello,\n\n"
        "You requested a username reminder for SingleCell Explorer.\n\n"
        f"Your username is: {username}\n\n"
        + (f"Sign in here:\n{base}\n\n" if base else "")
        + "If you did not request this message, you can ignore it.\n\n"
        "SingleCell Explorer Security Team"
    )
    html = f"""
    <html><body style="font-family:Arial,sans-serif;line-height:1.5;">
      <h3>Your SingleCell Explorer username</h3>
      <p>Hello,</p>
      <p>Your username is: <strong>{username}</strong></p>
      {"<p><a href='" + base + "'>Open SingleCell Explorer</a></p>" if base else ""}
      <p>If you did not request this message, you can ignore it.</p>
      <p>SingleCell Explorer Security Team</p>
    </body></html>
    """
    return send_email(to_email, "Your SingleCell Explorer username", body, html)
