import json
import os
import secrets
import time


def _cfg(key: str, default: str = ""):
    env_val = os.getenv(key, "").strip()
    if env_val:
        return env_val
    try:
        from utils.backend_db import get_system_setting

        return get_system_setting(f"entra.{key.lower()}", default)
    except Exception:
        return default


def _get_query_params():
    try:
        import streamlit as st

        qp = st.query_params
        return {k: qp.get(k) for k in qp}
    except Exception:
        try:
            import streamlit as st

            qp = st.experimental_get_query_params()
            return {k: (v[0] if isinstance(v, list) and v else v) for k, v in qp.items()}
        except Exception:
            return {}


def _clear_query_params():
    try:
        import streamlit as st

        st.query_params.clear()
        return
    except Exception:
        try:
            import streamlit as st

            st.experimental_set_query_params()
        except Exception:
            pass


def entra_enabled():
    required = [
        "ENTRA_TENANT_ID",
        "ENTRA_CLIENT_ID",
        "ENTRA_CLIENT_SECRET",
        "ENTRA_REDIRECT_URI",
    ]
    return all(_cfg(key) for key in required)


def _team_map():
    raw = _cfg("ENTRA_TEAM_GROUP_MAP", "{}").strip()
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _admin_group():
    return _cfg("ENTRA_ADMIN_GROUP_ID")


def _auth_url():
    tenant = _cfg("ENTRA_TENANT_ID")
    return f"https://login.microsoftonline.com/{tenant}"


def _msal_app():
    import msal

    return msal.ConfidentialClientApplication(
        client_id=_cfg("ENTRA_CLIENT_ID"),
        client_credential=_cfg("ENTRA_CLIENT_SECRET"),
        authority=_auth_url(),
    )


def build_entra_login_url(state: str):
    app = _msal_app()
    return app.get_authorization_request_url(
        scopes=["openid", "profile", "email"],
        redirect_uri=_cfg("ENTRA_REDIRECT_URI"),
        state=state,
        prompt="select_account",
    )


def consume_entra_callback(expected_state: str):
    qp = _get_query_params()
    if "code" not in qp:
        return None, None
    state = qp.get("state", "")
    if expected_state and state != expected_state:
        _clear_query_params()
        return None, "Invalid Entra login state."

    app = _msal_app()
    token = app.acquire_token_by_authorization_code(
        code=qp.get("code"),
        scopes=["openid", "profile", "email"],
        redirect_uri=_cfg("ENTRA_REDIRECT_URI"),
    )
    _clear_query_params()
    if "id_token_claims" not in token:
        return None, token.get("error_description", "Failed to complete Entra login.")
    claims = token["id_token_claims"]
    now = int(time.time())
    skew = int(_cfg("ENTRA_CLOCK_SKEW_SECONDS", "120"))
    exp = int(claims.get("exp", 0) or 0)
    nbf = int(claims.get("nbf", 0) or 0)
    if exp and now > exp + skew:
        return None, "Entra token has expired. Please sign in again."
    if nbf and now + skew < nbf:
        return None, "Entra token is not yet valid."
    profile = map_claims_to_profile(claims)
    return profile, None


def map_claims_to_profile(claims: dict):
    username = (
        claims.get("preferred_username")
        or claims.get("upn")
        or claims.get("email")
        or claims.get("sub")
        or "entra_user"
    ).strip().lower()
    email = (claims.get("email") or claims.get("preferred_username") or claims.get("upn") or "").strip().lower()
    groups = claims.get("groups", []) or []
    if isinstance(groups, str):
        groups = [groups]

    admin_group = _admin_group()
    team_group_map = _team_map()
    role = "individual"
    team = None

    if admin_group and admin_group in groups:
        role = "organization"
        team = "Platform Admin"
    else:
        for gid, team_name in team_group_map.items():
            if gid in groups:
                role = "team"
                team = team_name
                break

    return {"username": username, "email": email, "role": role, "team": team, "login_mode": "Entra"}


def new_state_token():
    return secrets.token_urlsafe(24)
