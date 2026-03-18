import os

import streamlit as st
from utils.entra_auth import (
    build_entra_login_url,
    consume_entra_callback,
    entra_enabled,
    new_state_token,
)

PLATFORM_ADMIN_USERNAME = os.getenv("PLATFORM_ADMIN_USERNAME", "simon_admin").strip().lower()

DEMO_USERS = {
    "analyst": {"password": "demo123", "team": None, "role": "individual"},
    "teamlead": {"password": "demo123", "team": "Oncology Team", "role": "team"},
    "member1": {"password": "demo123", "team": "Oncology Team", "role": "team"},
    "deptadmin": {"password": "demo123", "team": "Pathology Department", "role": "organization"},
    "orgadmin": {"password": "demo123", "team": "Pathology Department", "role": "organization"},
}
ROLE_ORDER = {"individual": 1, "team": 2, "organization": 3}


def init_auth_state():
    defaults = {
        "is_authenticated": False,
        "auth_username": None,
        "auth_role": "individual",
        "auth_team": None,
        "auth_login_mode": "Individual",
        "auth_session_id": None,
        "auth_is_demo": False,
        "auth_email": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    return {key: st.session_state[key] for key in defaults}


def _norm(value: str):
    return " ".join((value or "").strip().lower().split())


def authenticate_demo_user(username: str, password: str, login_mode: str, team_name: str = ""):
    normalized_username = _norm(username)
    user = DEMO_USERS.get(_norm(username))
    if not user or user["password"] != password:
        return None, "Invalid username or password."
    mode = (login_mode or "Individual").strip().lower()
    if mode == "team":
        if user["team"] is None:
            return None, "This account is not a team member. Use Individual mode or a team account."
        if not team_name.strip():
            return None, "Team name is required for Team login."
        if _norm(user["team"]) != _norm(team_name):
            return None, f"Team mismatch for {normalized_username}. Expected team: {user['team']}."
    elif mode != "individual":
        return None, "Invalid login mode."
    return {
        "username": normalized_username,
        "email": f"{normalized_username}@demo.local",
        "role": user["role"],
        "team": user["team"],
    }, None


def authenticate_registered_user(username: str, password: str, login_mode: str, team_name: str = ""):
    try:
        from utils.backend_db import authenticate_user_account

        return authenticate_user_account(username, password, login_mode, team_name)
    except Exception:
        return None, "Account backend unavailable."


def logout_user():
    session_id = st.session_state.get("auth_session_id")
    try:
        from utils.backend_db import end_user_session

        end_user_session(session_id)
    except Exception:
        pass
    st.session_state["is_authenticated"] = False
    st.session_state["auth_username"] = None
    st.session_state["auth_role"] = "individual"
    st.session_state["auth_team"] = None
    st.session_state["auth_login_mode"] = "Individual"
    st.session_state["auth_session_id"] = None
    st.session_state["auth_is_demo"] = False
    st.session_state["auth_email"] = None
    try:
        remember = {}
        for key in ("remember_user", "remember_mode", "remember_team"):
            value = st.query_params.get(key)
            if value:
                remember[key] = value
        st.query_params.clear()
        for key, value in remember.items():
            st.query_params[key] = value
    except Exception:
        pass
    for key in ("workspace_type", "workspace_name", "workspace_owner", "shared_snapshots"):
        if key in st.session_state:
            del st.session_state[key]


def get_current_user():
    init_auth_state()
    return {
        "username": st.session_state.get("auth_username"),
        "role": st.session_state.get("auth_role"),
        "team": st.session_state.get("auth_team"),
        "login_mode": st.session_state.get("auth_login_mode", "Individual"),
        "session_id": st.session_state.get("auth_session_id"),
        "is_demo": st.session_state.get("auth_is_demo", False),
        "email": st.session_state.get("auth_email"),
    }


def is_platform_admin(user=None):
    current = user or get_current_user()
    current_name = (current.get("username") or "").strip().lower()
    configured_name = PLATFORM_ADMIN_USERNAME
    try:
        from utils.backend_db import get_platform_admin_username

        configured_name = get_platform_admin_username(PLATFORM_ADMIN_USERNAME)
    except Exception:
        pass
    return current_name == configured_name


def has_role(user_role: str, minimum_role: str):
    return ROLE_ORDER.get(user_role or "individual", 0) >= ROLE_ORDER.get(minimum_role, 0)


def require_min_role(minimum_role: str, feature_name: str):
    user = get_current_user()
    if has_role(user.get("role"), minimum_role):
        return user
    st.error(f"{feature_name} requires {minimum_role} role access.")
    st.stop()


def render_login_gate():
    init_auth_state()
    if st.session_state.get("is_authenticated"):
        return

    try:
        sid = st.query_params.get("auth_sid")
    except Exception:
        sid = None
    if sid:
        try:
            from utils.backend_db import get_active_session, get_user_by_username

            sess = get_active_session(sid)
            if sess:
                user_row = get_user_by_username(sess["username"])
                st.session_state["is_authenticated"] = True
                st.session_state["auth_username"] = sess["username"]
                st.session_state["auth_role"] = sess["role"]
                st.session_state["auth_team"] = sess["team"] if sess["team"] != "individual" else None
                st.session_state["auth_login_mode"] = sess["login_mode"]
                st.session_state["auth_session_id"] = sess["session_id"]
                st.session_state["auth_is_demo"] = str(user_row.get("email", "")).endswith("@demo.local") if user_row else False
                st.session_state["auth_email"] = user_row.get("email") if user_row else None
                return
        except Exception:
            pass

    st.markdown("## 🔐 Login required")
    if "entra_login_state" not in st.session_state:
        st.session_state["entra_login_state"] = new_state_token()

    if entra_enabled():
        profile, entra_error = consume_entra_callback(st.session_state["entra_login_state"])
        if profile:
            st.session_state["is_authenticated"] = True
            st.session_state["auth_username"] = profile["username"]
            st.session_state["auth_role"] = profile["role"]
            st.session_state["auth_team"] = profile["team"]
            st.session_state["auth_login_mode"] = profile["login_mode"]
            st.session_state["auth_is_demo"] = False
            st.session_state["auth_email"] = profile.get("email")
            try:
                from utils.backend_db import bootstrap_demo_users, start_user_session

                bootstrap_demo_users(DEMO_USERS)
                st.session_state["auth_session_id"] = start_user_session(
                    username=profile["username"],
                    login_mode=profile["login_mode"],
                    team=profile["team"] or "individual",
                    role=profile["role"],
                )
                try:
                    st.query_params["auth_sid"] = st.session_state["auth_session_id"]
                except Exception:
                    pass
            except Exception:
                st.session_state["auth_session_id"] = None
            if profile["team"]:
                st.switch_page("pages/9_Team_Dashboard.py")
            st.rerun()
        if entra_error:
            st.error(entra_error)
    st.markdown("Use **Sign in** for existing accounts, or create and verify a new account below.")
    st.caption("Demo users: analyst/teamlead/member1/deptadmin/orgadmin (password demo123).")
    st.caption("Platform admin credentials are managed in the separate admin backend app (default port 8601).")
    try:
        from utils.mailer import mail_enabled

        if not mail_enabled():
            st.warning("Email service is not configured yet. Verification/reset will use one-time token fallback.")
    except Exception:
        pass
    try:
        qp = st.query_params
        if qp.get("verify_user") and qp.get("verify_token"):
            st.info("Verification link detected. Open 'Verify email' below and submit.")
            st.session_state["verify_user"] = qp.get("verify_user")
            st.session_state["verify_token"] = qp.get("verify_token")
        if qp.get("reset_email") and qp.get("reset_token"):
            st.info("Password reset link detected. Open 'Reset password' below and submit.")
            st.session_state["reset_email"] = qp.get("reset_email")
            st.session_state["reset_token"] = qp.get("reset_token")
    except Exception:
        pass
    if entra_enabled():
        st.link_button(
            "Sign in with Microsoft Entra ID",
            url=build_entra_login_url(st.session_state["entra_login_state"]),
            use_container_width=True,
        )
        st.caption("Entra sign-in uses OIDC + MFA policy from your tenant.")
    tab_signin, tab_create, tab_verify, tab_forgot, tab_reset = st.tabs(
        ["Sign in", "Create account", "Verify email", "Forgot password", "Reset password"]
    )

    with tab_signin:
        prefill_user = st.query_params.get("remember_user", "")
        prefill_mode = st.query_params.get("remember_mode", "Individual")
        prefill_team = st.query_params.get("remember_team", "")
        with st.form("login_form", clear_on_submit=False):
            login_mode = st.radio(
                "Login as",
                ["Individual", "Team"],
                horizontal=True,
                index=1 if prefill_mode == "Team" else 0,
            )
            username = st.text_input("Username", value=prefill_user, placeholder="e.g. analyst or teamlead")
            password = st.text_input("Password", type="password")
            team_name = st.text_input(
                "Team name",
                value=prefill_team if prefill_mode == "Team" else "",
                placeholder="e.g. Oncology Team",
                disabled=login_mode != "Team",
            )
            remember_login = st.checkbox("Remember username/team on this device", value=bool(prefill_user))
            if login_mode == "Team":
                st.caption("Demo team names: Oncology Team, Pathology Department.")
            submitted = st.form_submit_button("Login", type="primary", use_container_width=True)
        if submitted:
            user, error = authenticate_registered_user(username, password, login_mode, team_name)
            is_demo = False
            if user is None:
                user, error = authenticate_demo_user(username, password, login_mode, team_name)
                is_demo = user is not None
            if user is None:
                st.error(error or "Invalid login details for the selected mode/team.")
            else:
                st.session_state["is_authenticated"] = True
                st.session_state["auth_username"] = user["username"]
                st.session_state["auth_role"] = user["role"]
                st.session_state["auth_team"] = user["team"]
                st.session_state["auth_login_mode"] = login_mode
                st.session_state["auth_is_demo"] = is_demo
                st.session_state["auth_email"] = user.get("email")
                try:
                    from utils.backend_db import bootstrap_demo_users, start_user_session

                    bootstrap_demo_users(DEMO_USERS)
                    st.session_state["auth_session_id"] = start_user_session(
                        username=user["username"],
                        login_mode=login_mode,
                        team=user["team"] or "individual",
                        role=user["role"],
                    )
                    try:
                        if remember_login:
                            st.query_params["remember_user"] = user["username"]
                            st.query_params["remember_mode"] = login_mode
                            if login_mode == "Team":
                                st.query_params["remember_team"] = team_name.strip()
                            elif st.query_params.get("remember_team"):
                                del st.query_params["remember_team"]
                        else:
                            for key in ("remember_user", "remember_mode", "remember_team"):
                                if st.query_params.get(key):
                                    del st.query_params[key]
                        st.query_params["auth_sid"] = st.session_state["auth_session_id"]
                    except Exception:
                        pass
                except Exception:
                    st.session_state["auth_session_id"] = None
                if user["team"] and login_mode == "Team":
                    st.switch_page("pages/9_Team_Dashboard.py")
                st.rerun()

    with tab_create:
        with st.form("register_form", clear_on_submit=True):
            reg_username = st.text_input("New username")
            reg_email = st.text_input("Email address", placeholder="name@organization.org")
            reg_password = st.text_input("New password", type="password")
            reg_password_confirm = st.text_input("Confirm password", type="password")
            in_group = st.radio("Do you belong to a group/team?", ["No", "Yes"], horizontal=True)
            reg_team = st.text_input(
                "Team name",
                placeholder="e.g. Oncology Team",
                disabled=in_group != "Yes",
            )
            reg_submit = st.form_submit_button("Create account", type="primary", use_container_width=True)
        if reg_submit:
            if reg_password != reg_password_confirm:
                st.error("Passwords do not match.")
            else:
                try:
                    from utils.backend_db import issue_email_verification_token, register_user_account

                    ok, err = register_user_account(
                        reg_username,
                        reg_password,
                        reg_email,
                        reg_team if in_group == "Yes" else "",
                    )
                except Exception:
                    ok, err = False, "Failed to create account."
                if ok:
                    try:
                        token, token_err = issue_email_verification_token(reg_username)
                    except Exception:
                        token, token_err = None, "Verification token unavailable."
                    if token:
                        try:
                            from utils.backend_db import get_user_by_username
                            from utils.mailer import mail_enabled, send_verification_email

                            user_row = get_user_by_username(reg_username.strip().lower())
                            if user_row and user_row.get("email") and mail_enabled():
                                sent, mail_err = send_verification_email(
                                    user_row["email"], user_row["username"], token
                                )
                                if sent:
                                    st.success("Account created. Verification email sent.")
                                else:
                                    st.error(f"Account created, but email delivery failed: {mail_err}")
                                    st.caption("Use fallback verification token below.")
                                    st.code(token)
                            else:
                                st.warning("Account created. SMTP not configured; using verification token fallback.")
                                st.code(token)
                        except Exception:
                            st.warning("Account created. Email service unavailable; using verification token fallback.")
                            st.code(token)
                    else:
                        st.warning("Account created, but verification token could not be issued.")
                        if token_err:
                            st.caption(token_err)
                else:
                    st.error(err or "Unable to create account.")

    with tab_verify:
        with st.form("verify_email_form", clear_on_submit=True):
            v_user = st.text_input("Username", key="verify_user")
            v_token = st.text_input("Verification token", key="verify_token")
            v_submit = st.form_submit_button("Verify email", use_container_width=True)
        if v_submit:
            try:
                from utils.backend_db import verify_email_with_token

                ok, err = verify_email_with_token(v_user, v_token)
            except Exception:
                ok, err = False, "Verification failed."
            if ok:
                st.success("Email verified. You can now login.")
            else:
                st.error(err or "Verification failed.")

    with tab_forgot:
        with st.form("forgot_pw_form", clear_on_submit=True):
            fp_email = st.text_input("Account email")
            fp_submit = st.form_submit_button("Request reset token", use_container_width=True)
        if fp_submit:
            try:
                from utils.backend_db import issue_password_reset_token
                from utils.mailer import mail_enabled, send_password_reset_email

                token, err = issue_password_reset_token(fp_email)
            except Exception:
                token, err = None, "Password reset is unavailable."
            if token:
                if mail_enabled():
                    try:
                        from utils.backend_db import get_user_by_email

                        user_row = get_user_by_email(fp_email)
                        if user_row:
                            send_password_reset_email(user_row["email"], user_row["username"], token)
                    except Exception:
                        pass
                    st.success("If the email exists, a password reset message has been sent.")
                else:
                    st.warning("SMTP not configured; using reset token fallback.")
                    st.code(token)
            else:
                st.success("If the email exists, a password reset message has been sent.")

    with tab_reset:
        with st.form("reset_pw_form", clear_on_submit=True):
            rp_email = st.text_input("Account email", key="reset_email")
            rp_token = st.text_input("Reset token", key="reset_token")
            rp_new = st.text_input("New password", type="password", key="reset_new")
            rp_new2 = st.text_input("Confirm new password", type="password", key="reset_new2")
            rp_submit = st.form_submit_button("Reset password", use_container_width=True)
        if rp_submit:
            if rp_new != rp_new2:
                st.error("Passwords do not match.")
            else:
                try:
                    from utils.backend_db import reset_password_with_email_token

                    ok, err = reset_password_with_email_token(rp_email, rp_token, rp_new)
                except Exception:
                    ok, err = False, "Password reset failed."
                if ok:
                    st.success("Password reset successful. You can now login.")
                else:
                    st.error(err or "Password reset failed.")
    st.stop()
