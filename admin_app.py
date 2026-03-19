import pandas as pd
import streamlit as st
from datetime import datetime, timezone
from pathlib import Path
import os
from uuid import uuid4

from utils.backend_db import (
    admin_create_user_account,
    backend_overview,
    configure_platform_admin,
    emergency_reset_platform_admin,
    fetch_rows,
    get_platform_admin_username,
    get_system_setting,
    get_system_settings,
    hash_password,
    init_db,
    insert_audit_event,
    migrate_collab_store,
    set_system_setting,
    set_platform_admin_password,
)

st.set_page_config(page_title="Platform Admin Backend", layout="wide")
init_db()


def _admin_exists():
    rows = fetch_rows("SELECT username FROM users WHERE role = 'organization' ORDER BY created_at ASC LIMIT 1")
    return rows[0]["username"] if rows else ""


def _log_admin_event(event_type: str, actor: str, details: dict):
    insert_audit_event(
        {
            "id": str(uuid4()),
            "event_type": event_type,
            "actor": actor or "platform_admin",
            "team": "platform_admin",
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        }
    )


st.title("🛡️ Platform Admin Backend")
st.caption("Run this separately from main app. Recommended: streamlit run admin_app.py --server.port 8601")
recovery_env_key = os.getenv("PLATFORM_ADMIN_RECOVERY_KEY", "").strip()

admin_seed = _admin_exists()
configured_admin = get_platform_admin_username("")
st.markdown("### Platform admin credentials")
with st.form("platform_admin_setup", clear_on_submit=True):
    setup_user = st.text_input(
        "Platform admin username",
        value=configured_admin or "",
        placeholder="your_admin_user",
    )
    setup_pass = st.text_input("Set new admin password", type="password")
    setup_pass2 = st.text_input("Confirm new admin password", type="password")
    current_pass = st.text_input(
        "Current admin password (required if admin already configured)",
        type="password",
    )
    forgot_mode = st.checkbox("I forgot the current admin password")
    recovery_key = st.text_input("Recovery key", type="password", disabled=not forgot_mode)
    setup_submit = st.form_submit_button("Save admin credentials", type="primary")
if setup_submit:
    if not setup_user.strip() or not setup_pass:
        st.error("Username and password are required.")
    elif setup_pass != setup_pass2:
        st.error("Passwords do not match.")
    else:
        recovery_ok = bool(recovery_env_key and forgot_mode and recovery_key == recovery_env_key)
        ok, err = configure_platform_admin(
            username=setup_user.strip().lower(),
            password=setup_pass,
            current_password=current_pass,
            bypass_current_password=bool(
                st.session_state.get("admin_auth")
                and st.session_state.get("admin_user")
                and st.session_state.get("admin_user") == configured_admin
            )
            or recovery_ok,
        )
        if ok:
            st.success("Platform admin credentials saved.")
            st.rerun()
        else:
            st.error(err or "Failed to save admin credentials.")
            if forgot_mode and not recovery_env_key:
                st.info("Recovery key is not configured. Set PLATFORM_ADMIN_RECOVERY_KEY in the environment and restart admin app.")

with st.expander("Emergency reset existing backend admin login", expanded=False):
    st.warning("Use this only if you are locked out. This disables existing organization admin logins.")
    with st.form("emergency_admin_reset_form", clear_on_submit=True):
        confirm_text = st.text_input("Type RESET to confirm")
        reset_submit = st.form_submit_button("Reset existing admin login")
    if reset_submit:
        if (confirm_text or "").strip().upper() != "RESET":
            st.error("Confirmation text mismatch.")
        else:
            emergency_reset_platform_admin()
            st.session_state["admin_auth"] = False
            st.session_state["admin_user"] = ""
            st.success("Existing backend admin login reset. You can now create new platform admin credentials above.")
            st.rerun()

if not admin_seed:
    st.info("No backend users found yet. Create admin credentials above, then login.")

if "admin_auth" not in st.session_state:
    st.session_state["admin_auth"] = False
if "admin_user" not in st.session_state:
    st.session_state["admin_user"] = ""

if not st.session_state["admin_auth"]:
    st.markdown("### Admin login")
    with st.form("admin_login"):
        login_user = st.text_input("Username")
        login_pass = st.text_input("Password", type="password")
        login_submit = st.form_submit_button("Login", type="primary")
    if login_submit:
        from utils.backend_db import authenticate_platform_admin

        if authenticate_platform_admin(login_user.strip().lower(), login_pass):
            st.session_state["admin_auth"] = True
            st.session_state["admin_user"] = login_user.strip().lower()
            st.rerun()
        st.error("Invalid admin credentials.")
    st.stop()

st.success(f"Logged in as {st.session_state['admin_user']}")

with st.expander("Change admin password", expanded=False):
    with st.form("change_password_form", clear_on_submit=True):
        current_pw = st.text_input("Current password", type="password")
        new_pw = st.text_input("New password", type="password")
        new_pw2 = st.text_input("Confirm new password", type="password")
        change_submit = st.form_submit_button("Update password")
    if change_submit:
        if not new_pw:
            st.error("New password cannot be empty.")
        elif new_pw != new_pw2:
            st.error("New passwords do not match.")
        elif set_platform_admin_password(st.session_state["admin_user"], current_pw, new_pw):
            st.success("Password updated successfully.")
        else:
            st.error("Current password is incorrect.")

with st.expander("Create backend user account", expanded=False):
    with st.form("admin_create_user_form", clear_on_submit=True):
        new_u = st.text_input("Username")
        new_e = st.text_input("Email")
        new_p = st.text_input("Temporary password", type="password")
        new_r = st.selectbox("Role", ["individual", "team", "organization"])
        new_t = st.text_input("Team name (optional)")
        new_verified = st.checkbox("Mark email as verified", value=True)
        new_active = st.checkbox("Active account", value=True)
        send_verify_mail = st.checkbox("Send verification email now (requires SMTP)", value=False)
        create_submit = st.form_submit_button("Create account", type="primary", use_container_width=True)
    st.caption("Requirements: unique username/email and password with at least 8 characters.")
    if create_submit:
        ok, err = admin_create_user_account(
            username=new_u,
            email=new_e,
            password=new_p,
            role=new_r,
            team_name=new_t,
            email_verified=new_verified,
            is_active=new_active,
        )
        if ok:
            st.success("Backend user account created.")
            if send_verify_mail:
                from utils.backend_db import issue_email_verification_token
                from utils.mailer import mail_enabled, send_verification_email

                token, token_err = issue_email_verification_token((new_u or "").strip().lower())
                if token and mail_enabled():
                    sent, mail_err = send_verification_email(
                        (new_e or "").strip().lower(),
                        (new_u or "").strip().lower(),
                        token,
                    )
                    if sent:
                        st.success("Verification email sent.")
                    else:
                        st.error(f"Created account, but verification email failed: {mail_err}")
                elif token:
                    st.warning("Created account, but SMTP is not configured for email sending.")
                    st.code(token)
                elif token_err and "already verified" not in (token_err or "").lower():
                    st.warning(f"Created account, but token generation failed: {token_err}")
            _log_admin_event(
                "admin_user_create_success",
                st.session_state.get("admin_user"),
                {"username": (new_u or "").strip().lower(), "email": (new_e or "").strip().lower(), "role": new_r},
            )
            st.rerun()
        else:
            _log_admin_event(
                "admin_user_create_failed",
                st.session_state.get("admin_user"),
                {
                    "username": (new_u or "").strip().lower(),
                    "email": (new_e or "").strip().lower(),
                    "role": new_r,
                    "error": err or "unknown_error",
                },
            )
            st.error(err or "Failed to create account.")

c1, c2 = st.columns(2)
with c1:
    if st.button("Migrate current JSON data to backend", use_container_width=True):
        result = migrate_collab_store()
        st.success(f"Migrated {result['records']} records and {result['events']} audit events.")
with c2:
    if st.button("Logout", use_container_width=True):
        st.session_state["admin_auth"] = False
        st.session_state["admin_user"] = ""
        st.rerun()

with st.expander("Backend configuration (SMTP + Entra)", expanded=False):
    with st.form("smtp_config_form"):
        smtp_host = st.text_input("SMTP Host", value=get_system_setting("mail.smtp_host"))
        smtp_port = st.text_input("SMTP Port", value=get_system_setting("mail.smtp_port", "587"))
        smtp_username = st.text_input("SMTP Username", value=get_system_setting("mail.smtp_username"))
        smtp_password = st.text_input("SMTP Password", type="password", value=get_system_setting("mail.smtp_password"))
        smtp_from = st.text_input("SMTP From Email", value=get_system_setting("mail.smtp_from_email"))
        smtp_ssl = st.selectbox(
            "SMTP Use SSL",
            ["false", "true"],
            index=1 if get_system_setting("mail.smtp_use_ssl", "false") == "true" else 0,
        )
        smtp_starttls = st.selectbox(
            "SMTP Use STARTTLS",
            ["true", "false"],
            index=0 if get_system_setting("mail.smtp_use_starttls", "true") == "true" else 1,
        )
        smtp_timeout = st.text_input("SMTP Timeout (seconds)", value=get_system_setting("mail.smtp_timeout_seconds", "10"))
        app_public_url = st.text_input("App Public URL", value=get_system_setting("mail.app_public_url"))
        save_smtp = st.form_submit_button("Save SMTP settings", use_container_width=True)
        test_to = st.text_input("SMTP test recipient email")
        test_smtp = st.form_submit_button("Send test email", use_container_width=True)
    if save_smtp:
        set_system_setting("mail.smtp_host", smtp_host.strip())
        set_system_setting("mail.smtp_port", smtp_port.strip())
        set_system_setting("mail.smtp_username", smtp_username.strip())
        set_system_setting("mail.smtp_password", smtp_password.strip())
        set_system_setting("mail.smtp_from_email", smtp_from.strip())
        set_system_setting("mail.smtp_use_ssl", smtp_ssl.strip())
        set_system_setting("mail.smtp_use_starttls", smtp_starttls.strip())
        set_system_setting("mail.smtp_timeout_seconds", smtp_timeout.strip() or "10")
        set_system_setting("mail.app_public_url", app_public_url.strip())
        st.success("SMTP/backend email settings saved.")
    if test_smtp:
        from utils.mailer import send_email

        if not (test_to or "").strip():
            st.error("Enter a recipient email for SMTP test.")
        else:
            sent, err = send_email(
                test_to,
                "SingleCell Explorer SMTP Test",
                "This is a test email from the Platform Admin backend.",
            )
            if sent:
                _log_admin_event("smtp_test_success", st.session_state.get("admin_user"), {"to": test_to.strip().lower()})
                st.success("Test email sent successfully.")
            else:
                _log_admin_event(
                    "smtp_test_failed",
                    st.session_state.get("admin_user"),
                    {"to": test_to.strip().lower(), "error": err or "unknown_error"},
                )
                st.error(f"SMTP test failed: {err}")

    from utils.mailer import get_mail_diagnostics

    diag = get_mail_diagnostics()
    if not diag["enabled"]:
        missing = ", ".join(diag.get("missing_fields", [])) or "unknown"
        st.warning(f"SMTP not fully configured. Missing: {missing}")
    else:
        st.success("SMTP is configured.")
    st.caption("SMTP diagnostics")
    st.dataframe(
        pd.DataFrame(
            [
                {"check": "SMTP enabled", "value": str(diag["enabled"])},
                {"check": "Host", "value": diag["host"] or "(missing)"},
                {"check": "Port", "value": diag["port"] or "(missing)"},
                {"check": "Username set", "value": str(diag["username_set"])},
                {"check": "Password set", "value": str(diag["password_set"])},
                {"check": "From email", "value": diag["from_email"] or "(missing)"},
                {"check": "Use SSL", "value": str(diag["use_ssl"])},
                {"check": "Use STARTTLS", "value": str(diag["use_starttls"])},
                {"check": "SMTP timeout seconds", "value": str(diag["timeout_seconds"])},
                {"check": "App public URL", "value": diag["app_public_url"] or "(optional)"},
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(f"Database path: {Path('data/platform_backend.db').resolve()}")

    with st.form("entra_config_form"):
        tenant_id = st.text_input("Entra Tenant ID", value=get_system_setting("entra.entra_tenant_id"))
        client_id = st.text_input("Entra Client ID", value=get_system_setting("entra.entra_client_id"))
        client_secret = st.text_input("Entra Client Secret", type="password", value=get_system_setting("entra.entra_client_secret"))
        redirect_uri = st.text_input("Entra Redirect URI", value=get_system_setting("entra.entra_redirect_uri"))
        admin_group = st.text_input("Entra Admin Group ID", value=get_system_setting("entra.entra_admin_group_id"))
        team_map = st.text_area(
            "Entra Team Group Map (JSON)",
            value=get_system_setting("entra.entra_team_group_map", "{}"),
            height=120,
        )
        save_entra = st.form_submit_button("Save Entra settings", use_container_width=True)
    if save_entra:
        set_system_setting("entra.entra_tenant_id", tenant_id.strip())
        set_system_setting("entra.entra_client_id", client_id.strip())
        set_system_setting("entra.entra_client_secret", client_secret.strip())
        set_system_setting("entra.entra_redirect_uri", redirect_uri.strip())
        set_system_setting("entra.entra_admin_group_id", admin_group.strip())
        set_system_setting("entra.entra_team_group_map", team_map.strip())
        st.success("Entra settings saved.")

    settings_rows = get_system_settings()
    if settings_rows:
        display_rows = []
        for row in settings_rows:
            value = row["value"]
            if any(x in row["key"] for x in ("password", "secret")):
                value = "********"
            display_rows.append({"key": row["key"], "value": value, "updated_at": row["updated_at"]})
        st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)

overview = backend_overview()
st.divider()
m1, m2, m3, m4 = st.columns(4)
m1.metric("Users", len(overview["users"]))
m2.metric("Teams", len(overview["teams"]))
m3.metric("Department Records", overview["record_count"])
m4.metric("Active Sessions", overview["active_sessions"])

st.markdown("### Users")
st.dataframe(pd.DataFrame(overview["users"]), use_container_width=True, hide_index=True)

st.markdown("### Memberships")
st.dataframe(pd.DataFrame(overview["memberships"]), use_container_width=True, hide_index=True)

st.markdown("### User Sessions")
st.dataframe(pd.DataFrame(overview["sessions"]), use_container_width=True, hide_index=True)

audit_rows = fetch_rows(
    "SELECT id, event_type, actor, team, created_at FROM audit_events ORDER BY created_at DESC LIMIT 200"
)
st.markdown("### Recent Audit Events")
st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)
