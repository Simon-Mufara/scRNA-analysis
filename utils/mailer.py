import os
import smtplib
import ssl
import time
import logging
from email.message import EmailMessage
from email.utils import formataddr
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse


logger = logging.getLogger(__name__)


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
        client = smtplib.SMTP_SSL(host, port, timeout=timeout, context=ssl.create_default_context())
    else:
        client = smtplib.SMTP(host, port, timeout=timeout)
        client.ehlo()
        if use_starttls:
            client.starttls(context=ssl.create_default_context())
            client.ehlo()
    client.login(username, password)
    return client


def send_email(to_email: str, subject: str, text_body: str, html_body: str = ""):
    normalized_to = (to_email or "").strip().lower()
    if not normalized_to:
        return False, "Recipient email is required."
    if any(c in normalized_to for c in ("\r", "\n")):
        return False, "Invalid recipient email."
    if not mail_enabled():
        return False, "SMTP is not configured."
    msg = EmailMessage()
    msg["Subject"] = subject
    from_email = _cfg("SMTP_FROM_EMAIL")
    msg["From"] = formataddr(("SingleCell Explorer", from_email))
    msg["To"] = normalized_to
    msg["Reply-To"] = from_email
    msg["X-Product"] = "SingleCell Clinical & Research Explorer"
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")
    retries = max(1, int(_cfg("SMTP_RETRY_COUNT", "2")))
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            with _smtp_client() as client:
                client.send_message(msg)
            logger.info("Email sent successfully: recipient=%s subject=%s", normalized_to, subject)
            return True, None
        except Exception as exc:
            last_error = str(exc)
            logger.error(
                "Email send failed: recipient=%s subject=%s attempt=%s/%s error=%s",
                normalized_to,
                subject,
                attempt,
                retries,
                last_error,
            )
            if attempt < retries:
                time.sleep(0.5)
    return False, last_error


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
    base = _cfg("FRONTEND_URL", "").strip().rstrip("/") or _cfg("APP_PUBLIC_URL", "").strip().rstrip("/")
    if base and not base.lower().startswith(("http://", "https://")):
        base = f"https://{base}"
    return base


def _build_app_url(base: str, params: dict):
    if not base:
        return ""
    q = urlencode({k: v for k, v in params.items() if str(v or "").strip()})
    if not q:
        return base
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}{q}"


def _safe_log_link(url: str):
    if not url:
        return ""
    parsed = urlparse(url)
    redacted = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower() in {"token", "verify_token", "reset_token"} and value:
            redacted.append((key, "***redacted***"))
        else:
            redacted.append((key, value))
    return urlunparse(parsed._replace(query=urlencode(redacted)))


def _support_contact():
    return _cfg("SUPPORT_EMAIL", "").strip() or _cfg("SMTP_FROM_EMAIL", "").strip()


def _support_text():
    support = _support_contact()
    return f"Need help? Contact support at {support}.\n" if support else "Need help? Contact your platform support team.\n"


def _support_html():
    support = _support_contact()
    if support:
        return f"<br><br><b>Support:</b> <a href='mailto:{support}'>{support}</a>"
    return "<br><br><b>Support:</b> Contact your platform support team."


def _brand_html_email(title: str, subtitle: str, body_html: str, cta_label: str = "", cta_url: str = "", code: str = ""):
    cta_block = (
        f"<p style='margin:20px 0;'><a href='{cta_url}' "
        "style='background:#00D4FF;color:#0B1220;text-decoration:none;padding:10px 16px;"
        "border-radius:8px;font-weight:700;display:inline-block;'>"
        f"{cta_label}</a></p>"
        if cta_label and cta_url
        else ""
    )
    code_block = (
        f"<p style='margin:10px 0 0;color:#8B949E;'>One-time code:</p>"
        f"<div style='font-size:22px;font-weight:800;letter-spacing:0.08em;color:#E6EDF3;"
        f"background:#0D1117;border:1px solid #30363D;border-radius:8px;padding:10px 12px;"
        f"display:inline-block;'>{code}</div>"
        if code
        else ""
    )
    return f"""
    <html>
      <body style="margin:0;padding:0;background:#070B14;font-family:Inter,Arial,sans-serif;color:#E6EDF3;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#070B14;padding:24px 0;">
          <tr><td align="center">
            <table role="presentation" width="620" cellpadding="0" cellspacing="0" style="max-width:620px;background:#0D1117;border:1px solid #21262D;border-radius:12px;overflow:hidden;">
              <tr>
                <td style="padding:16px 22px;background:linear-gradient(135deg,rgba(0,212,255,0.2),rgba(123,47,190,0.2));border-bottom:1px solid #21262D;">
                  <div style="font-size:16px;font-weight:800;color:#E6EDF3;">SingleCell Clinical &amp; Research Explorer</div>
                  <div style="font-size:12px;color:#C9D1D9;margin-top:4px;">{subtitle}</div>
                </td>
              </tr>
              <tr>
                <td style="padding:22px;">
                  <h2 style="margin:0 0 10px;font-size:22px;color:#E6EDF3;">{title}</h2>
                  <div style="font-size:14px;line-height:1.7;color:#C9D1D9;">{body_html}</div>
                  {code_block}
                  {cta_block}
                  <p style="margin-top:20px;font-size:12px;color:#8B949E;">
                    If you did not request this action, you can safely ignore this email.
                  </p>
                </td>
              </tr>
            </table>
          </td></tr>
        </table>
      </body>
    </html>
    """


def send_verification_email(to_email: str, username: str, token: str):
    base = _public_base_url()
    login_url = base
    verify_url = _build_app_url(f"{base}/verify" if base else "", {"token": token})
    logger.info("Generated verification link: recipient=%s link=%s", (to_email or "").strip().lower(), _safe_log_link(verify_url))
    body = (
        f"Hello {username},\n\n"
        "Welcome to SingleCell Clinical & Research Explorer.\n\n"
        "Your account has been created successfully.\n"
        + (f"Secure login link:\n{login_url}\n\n" if login_url else "")
        + "Please verify your email to activate secure sign-in.\n\n"
        + (f"Verify Account:\n{verify_url}\n\n" if verify_url else "")
        + "One-time verification code:\n"
        + f"{token}\n\n"
        + "Password reset instructions:\n"
        + "If you forget your password, use the 'Forgot password' option on the sign-in page to generate a secure reset link.\n"
        + "For your security, we will never send or share passwords by email.\n\n"
        + "Security Notice\n"
        + "- Passwords are encrypted using industry-standard hashing.\n"
        + "- Passwords are never stored in plain text.\n"
        + "- Do not share your credentials with anyone.\n\n"
        + _support_text()
        + "Your account security is our priority, and we monitor authentication systems continuously.\n\n"
        + "This code/link expires automatically for your security.\n\n"
        + "SingleCell Explorer Security Team"
    )
    html = _brand_html_email(
        title="Verify your account",
        subtitle="Account security confirmation",
        body_html=(
            f"Hello <b>{username}</b>,<br><br>"
            "Welcome to SingleCell Clinical &amp; Research Explorer. Your account has been created successfully."
            + (f"<br><br><b>Secure login link:</b> <a href='{login_url}'>{login_url}</a>" if login_url else "")
            + "<br><br>Please verify your email to activate secure access."
            + (f"<br><br><b>Verify Account:</b> <a href='{verify_url}'>{verify_url}</a>" if verify_url else "")
            + "<br><br><b>Password reset instructions:</b> If you forget your password, use the <i>Forgot password</i> option on the sign-in page to generate a secure reset link. We do not send or share passwords by email."
            + "<br><br><b>Security Notice</b><br>"
            + "&bull; Passwords are encrypted using industry-standard hashing.<br>"
            + "&bull; Passwords are never stored in plain text.<br>"
            + "&bull; Do not share your credentials with anyone."
            + _support_html()
            + "<br><br>Your account security is our priority, and we monitor authentication systems continuously."
        ),
        cta_label="Verify Account",
        cta_url=verify_url,
        code=token,
    )
    return send_email(to_email, "Action required: verify your SingleCell Explorer account", body, html)


def send_password_reset_email(to_email: str, username: str, token: str):
    base = _public_base_url()
    reset_url = _build_app_url(base, {"reset_email": to_email, "reset_token": token})
    logger.info("Generated password reset link: recipient=%s link=%s", (to_email or "").strip().lower(), _safe_log_link(reset_url))
    body = (
        f"Hello {username},\n\n"
        "We received a password reset request for your SingleCell Explorer account.\n\n"
        + (f"Reset Password:\n{reset_url}\n\n" if reset_url else "")
        + "Use this one-time reset token:\n"
        + f"{token}\n\n"
        + "For your security, we do not send or share passwords by email.\n"
        + "Security reassurance: your password is protected with encrypted hashing and never stored in plain text.\n"
        + _support_text()
        + "If you did not request this, you can ignore this email.\n\n"
        "SingleCell Explorer Security Team"
    )
    html = _brand_html_email(
        title="Reset your password",
        subtitle="Account recovery request",
        body_html=(
            f"Hello <b>{username}</b>,<br><br>"
            "We received a password reset request for your account."
            + (f"<br><br><b>Reset Password:</b> <a href='{reset_url}'>{reset_url}</a>" if reset_url else "")
            + "<br><br>For your security, we do not send or share passwords by email."
            + "<br><b>Security reassurance:</b> your password is protected with encrypted hashing and never stored in plain text."
            + _support_html()
        ),
        cta_label="Reset Password",
        cta_url=reset_url,
        code=token,
    )
    return send_email(to_email, "Reset your SingleCell Explorer password", body, html)


def send_password_reset_link_email(to_email: str, username: str, token: str):
    base = _public_base_url()
    reset_url = _build_app_url(f"{base}/reset-password" if base else "", {"token": token})
    logger.info("Generated password reset link: recipient=%s link=%s", (to_email or "").strip().lower(), _safe_log_link(reset_url))
    body = (
        f"Hello {username},\n\n"
        "We received a password reset request for your SingleCell Explorer account.\n\n"
        + (f"Reset Password:\n{reset_url}\n\n" if reset_url else "")
        + "For your security, we do not send or share passwords by email.\n"
        + "Security reassurance: your password is protected with encrypted hashing and never stored in plain text.\n"
        + _support_text()
        + "This reset link expires in 15 minutes.\n"
        "If you did not request this, you can ignore this email.\n\n"
        "SingleCell Explorer Security Team"
    )
    html = _brand_html_email(
        title="Reset your password",
        subtitle="Secure account recovery",
        body_html=(
            f"Hello <b>{username}</b>,<br><br>"
            "Use the secure link below to reset your password. This link expires in 15 minutes."
            + (f"<br><br><b>Reset Password:</b> <a href='{reset_url}'>{reset_url}</a>" if reset_url else "")
            + "<br><br>For your security, we do not send or share passwords by email."
            + "<br><b>Security reassurance:</b> your password is protected with encrypted hashing and never stored in plain text."
            + _support_html()
        ),
        cta_label="Reset Password",
        cta_url=reset_url,
    )
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
    html = _brand_html_email(
        title="Your username reminder",
        subtitle="Account access support",
        body_html=f"Hello,<br><br>Your username is: <b>{username}</b>.",
        cta_label="Open SingleCell Explorer",
        cta_url=base,
    )
    return send_email(to_email, "Your SingleCell Explorer username", body, html)
