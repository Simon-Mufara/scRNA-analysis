import json
import hashlib
import sqlite3
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "platform_backend.db"
COLLAB_STORE_PATH = Path(__file__).resolve().parents[1] / "data" / "collab_store.json"


def _now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                email_verified INTEGER NOT NULL DEFAULT 0,
                role TEXT NOT NULL,
                password_hash TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS team_memberships (
                user_id INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, team_id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(team_id) REFERENCES teams(id)
            );

            CREATE TABLE IF NOT EXISTS department_records (
                id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                owner TEXT NOT NULL,
                team TEXT NOT NULL,
                review_status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                team TEXT NOT NULL,
                details_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                login_mode TEXT NOT NULL,
                team TEXT NOT NULL,
                role TEXT NOT NULL,
                login_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                logout_at TEXT
            );

            CREATE TABLE IF NOT EXISTS auth_tokens (
                id TEXT PRIMARY KEY,
                token_type TEXT NOT NULL,
                username TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                expires_epoch INTEGER NOT NULL,
                used_epoch INTEGER,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "email" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
        if "email_verified" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0")


def _get_user_id(conn, username: str):
    row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    return row["id"] if row else None


def _get_team_id(conn, team_name: str):
    row = conn.execute("SELECT id FROM teams WHERE name = ?", (team_name,)).fetchone()
    return row["id"] if row else None


def upsert_user(username: str, role: str, password_hash: str = "", email: str = "", email_verified: int = 0):
    now = _now_utc()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO users (username, email, role, password_hash, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                email = excluded.email,
                role = excluded.role,
                password_hash = excluded.password_hash
            """,
            (username, email, role, password_hash, now),
        )
        if email_verified:
            conn.execute("UPDATE users SET email_verified = 1 WHERE username = ?", (username,))


def hash_password(password: str):
    salt = secrets.token_hex(16)
    iterations = 200_000
    digest = hashlib.pbkdf2_hmac("sha256", (password or "").encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str):
    if not password_hash:
        return False
    if password_hash.startswith("pbkdf2_sha256$"):
        try:
            _, iter_str, salt, expected_hex = password_hash.split("$", 3)
            iterations = int(iter_str)
            digest = hashlib.pbkdf2_hmac(
                "sha256",
                (password or "").encode("utf-8"),
                salt.encode("utf-8"),
                iterations,
            )
            return secrets.compare_digest(digest.hex(), expected_hex)
        except (ValueError, TypeError):
            return False
    legacy = hashlib.sha256((password or "").encode("utf-8")).hexdigest()
    return secrets.compare_digest(legacy, password_hash)


def _get_user_row(username: str):
    rows = fetch_rows(
        "SELECT username, email, email_verified, role, password_hash, is_active, created_at FROM users WHERE username = ?",
        (username,),
    )
    return rows[0] if rows else None


def _get_user_row_by_email(email: str):
    rows = fetch_rows(
        "SELECT username, email, email_verified, role, password_hash, is_active, created_at FROM users WHERE email = ?",
        ((email or "").strip().lower(),),
    )
    return rows[0] if rows else None


def get_user_by_username(username: str):
    return _get_user_row((username or "").strip().lower())


def get_user_by_email(email: str):
    return _get_user_row_by_email((email or "").strip().lower())


def ensure_team(team_name: str):
    if not team_name:
        return
    now = _now_utc()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO teams (name, created_at)
            VALUES (?, ?)
            ON CONFLICT(name) DO NOTHING
            """,
            (team_name, now),
        )


def assign_user_to_team(username: str, team_name: str, is_admin: bool = False):
    if not team_name:
        return
    now = _now_utc()
    with get_conn() as conn:
        user_id = _get_user_id(conn, username)
        team_id = _get_team_id(conn, team_name)
        if user_id is None or team_id is None:
            return
        conn.execute(
            """
            INSERT INTO team_memberships (user_id, team_id, is_admin, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, team_id) DO UPDATE SET is_admin = excluded.is_admin
            """,
            (user_id, team_id, 1 if is_admin else 0, now),
        )


def bootstrap_demo_users(demo_users: dict):
    init_db()
    for username, details in demo_users.items():
        role = details.get("role", "individual")
        team = details.get("team")
        upsert_user(
            username=username,
            role=role,
            email=f"{username}@demo.local",
            email_verified=1,
        )
        if team:
            ensure_team(team)
            assign_user_to_team(username=username, team_name=team, is_admin=(role == "organization"))


def ensure_platform_admin(username: str, password: str):
    init_db()
    set_system_setting("platform.admin_username", (username or "").strip().lower())
    existing = fetch_rows("SELECT username FROM users WHERE username = ?", (username,))
    if not existing:
        upsert_user(username=username, role="organization", password_hash=hash_password(password))
    else:
        with get_conn() as conn:
            conn.execute(
                "UPDATE users SET role = ?, password_hash = ? WHERE username = ?",
                ("organization", hash_password(password), username),
            )


def get_platform_admin_username(default: str = "simon_admin"):
    return get_system_setting("platform.admin_username", default).strip().lower()


def configure_platform_admin(
    username: str,
    password: str,
    current_password: str = "",
    bypass_current_password: bool = False,
):
    uname = (username or "").strip().lower()
    if not uname:
        return False, "Admin username is required."
    if len(password or "") < 8:
        return False, "Admin password must be at least 8 characters."

    current_admin = get_platform_admin_username("")
    if current_admin:
        # Existing admin configured: require current password to rotate credentials.
        if not bypass_current_password and not authenticate_platform_admin(current_admin, current_password):
            return False, "Current admin password is required to update admin credentials."

    set_system_setting("platform.admin_username", uname)
    upsert_user(uname, role="organization", password_hash=hash_password(password), email=f"{uname}@admin.local", email_verified=1)
    with get_conn() as conn:
        conn.execute("UPDATE users SET is_active = 1 WHERE username = ?", (uname,))
    return True, None


def authenticate_platform_admin(username: str, password: str):
    init_db()
    uname = (username or "").strip().lower()
    configured = get_platform_admin_username("")
    if configured and uname != configured:
        return False
    user = _get_user_row(uname)
    if not user:
        return False
    if not user.get("is_active") or user.get("role") != "organization":
        return False
    return verify_password(password, user.get("password_hash", ""))


def set_platform_admin_password(username: str, current_password: str, new_password: str):
    if not authenticate_platform_admin(username, current_password):
        return False
    with get_conn() as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE username = ?", (hash_password(new_password), username))
    return True


def emergency_reset_platform_admin():
    init_db()
    with get_conn() as conn:
        conn.execute("UPDATE users SET is_active = 0 WHERE role = 'organization'")
    set_system_setting("platform.admin_username", "")
    return True


def get_user_team(username: str):
    rows = fetch_rows(
        """
        SELECT t.name AS team
        FROM users u
        LEFT JOIN team_memberships m ON m.user_id = u.id
        LEFT JOIN teams t ON t.id = m.team_id
        WHERE u.username = ?
        ORDER BY m.is_admin DESC, m.created_at ASC
        LIMIT 1
        """,
        (username,),
    )
    return rows[0]["team"] if rows and rows[0].get("team") else None


def register_user_account(username: str, password: str, email: str, team_name: str = ""):
    init_db()
    uname = (username or "").strip().lower()
    if not uname:
        return False, "Username is required."
    if len(password or "") < 8:
        return False, "Password must be at least 8 characters."
    if _get_user_row(uname):
        return False, "Username already exists."
    email_clean = (email or "").strip().lower()
    if not email_clean or "@" not in email_clean:
        return False, "Valid email is required."
    email_exists = fetch_rows("SELECT username FROM users WHERE email = ?", (email_clean,))
    if email_exists:
        return False, "Email is already linked to another account."

    role = "team" if team_name.strip() else "individual"
    upsert_user(uname, role, hash_password(password), email=email_clean, email_verified=0)
    if team_name.strip():
        ensure_team(team_name.strip())
        assign_user_to_team(uname, team_name.strip(), is_admin=False)
    return True, None


def admin_create_user_account(
    username: str,
    email: str,
    password: str,
    role: str = "individual",
    team_name: str = "",
    email_verified: bool = True,
    is_active: bool = True,
):
    init_db()
    uname = (username or "").strip().lower()
    email_clean = (email or "").strip().lower()
    if not uname:
        return False, "Username is required."
    if not email_clean or "@" not in email_clean:
        return False, "Valid email is required."
    if len(password or "") < 8:
        return False, "Password must be at least 8 characters."
    existing = _get_user_row(uname)
    if existing and existing.get("email") and existing.get("email") != email_clean:
        return False, "Username already exists with a different email."
    email_owner = _get_user_row_by_email(email_clean)
    if email_owner and email_owner.get("username") != uname:
        return False, "Email is already linked to another account."

    normalized_role = (role or "individual").strip().lower()
    if normalized_role not in {"individual", "team", "organization"}:
        return False, "Invalid role."
    upsert_user(
        username=uname,
        role=normalized_role,
        password_hash=hash_password(password),
        email=email_clean,
        email_verified=1 if email_verified else 0,
    )
    with get_conn() as conn:
        conn.execute("UPDATE users SET is_active = ? WHERE username = ?", (1 if is_active else 0, uname))
    if team_name.strip():
        ensure_team(team_name.strip())
        assign_user_to_team(uname, team_name.strip(), is_admin=(normalized_role == "organization"))
    return True, None


def authenticate_user_account(username: str, password: str, login_mode: str, team_name: str = ""):
    init_db()
    identifier = (username or "").strip().lower()
    user = _get_user_row_by_email(identifier) if "@" in identifier else _get_user_row(identifier)
    if not user:
        return None, "Invalid username or password."
    uname = user["username"]
    if not user.get("is_active"):
        return None, "Account is inactive."
    if not user.get("email_verified"):
        return None, "Email is not verified. Verify your email before login."
    if not verify_password(password, user.get("password_hash", "")):
        return None, "Invalid username or password."

    team = get_user_team(uname)
    mode = (login_mode or "Individual").strip().lower()
    if mode == "team":
        if not team:
            return None, "This account is not assigned to a team."
        if not team_name.strip():
            return None, "Team name is required for Team login."
        if team.strip().lower() != team_name.strip().lower():
            return None, f"Team mismatch. Expected team: {team}."
    elif mode != "individual":
        return None, "Invalid login mode."

    role = user.get("role", "individual")
    return {"username": uname, "email": user.get("email"), "role": role, "team": team}, None


def _token_hash(raw_token: str):
    return hashlib.sha256((raw_token or "").encode("utf-8")).hexdigest()


def _issue_token(username: str, token_type: str, ttl_seconds: int):
    init_db()
    raw_token = secrets.token_urlsafe(24)
    token_id = str(uuid4())
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO auth_tokens (id, token_type, username, token_hash, expires_epoch, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (token_id, token_type, username, _token_hash(raw_token), int(time.time()) + ttl_seconds, _now_utc()),
        )
    return raw_token


def issue_email_verification_token(username: str):
    user = _get_user_row((username or "").strip().lower())
    if not user:
        return None, "User does not exist."
    if user.get("email_verified"):
        return None, "Email is already verified."
    return _issue_token(user["username"], "email_verify", 24 * 3600), None


def verify_email_with_token(username: str, token: str):
    uname = (username or "").strip().lower()
    if not uname or not token:
        return False, "Username and token are required."
    now_epoch = int(time.time())
    token_hash = _token_hash(token)
    rows = fetch_rows(
        """
        SELECT id FROM auth_tokens
        WHERE username = ? AND token_type = 'email_verify'
          AND token_hash = ? AND used_epoch IS NULL AND expires_epoch >= ?
        ORDER BY created_at DESC LIMIT 1
        """,
        (uname, token_hash, now_epoch),
    )
    if not rows:
        return False, "Invalid or expired verification token."
    token_id = rows[0]["id"]
    with get_conn() as conn:
        conn.execute("UPDATE users SET email_verified = 1 WHERE username = ?", (uname,))
        conn.execute("UPDATE auth_tokens SET used_epoch = ? WHERE id = ?", (now_epoch, token_id))
    return True, None


def issue_password_reset_token(email: str):
    email_clean = (email or "").strip().lower()
    user = _get_user_row_by_email(email_clean)
    if not user:
        return None, "No account found for this email."
    return _issue_token(user["username"], "password_reset", 1800), None


def issue_password_reset_token_for_username(username: str):
    user = _get_user_row((username or "").strip().lower())
    if not user or not user.get("email"):
        return None, "Account email is not available."
    token = _issue_token(user["username"], "password_reset", 1800)
    return {"token": token, "email": user["email"], "username": user["username"]}, None


def reset_password_with_token(username: str, token: str, new_password: str):
    uname = (username or "").strip().lower()
    if len(new_password or "") < 8:
        return False, "Password must be at least 8 characters."
    now_epoch = int(time.time())
    token_hash = _token_hash(token)
    rows = fetch_rows(
        """
        SELECT id FROM auth_tokens
        WHERE username = ? AND token_type = 'password_reset'
          AND token_hash = ? AND used_epoch IS NULL AND expires_epoch >= ?
        ORDER BY created_at DESC LIMIT 1
        """,
        (uname, token_hash, now_epoch),
    )
    if not rows:
        return False, "Invalid or expired reset token."
    token_id = rows[0]["id"]
    with get_conn() as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE username = ?", (hash_password(new_password), uname))
        conn.execute("UPDATE auth_tokens SET used_epoch = ? WHERE id = ?", (now_epoch, token_id))
    return True, None


def reset_password_with_email_token(email: str, token: str, new_password: str):
    user = _get_user_row_by_email(email)
    if not user:
        return False, "No account found for this email."
    return reset_password_with_token(user["username"], token, new_password)


def delete_user_account(username: str, password: str):
    init_db()
    uname = (username or "").strip().lower()
    user = _get_user_row(uname)
    if not user:
        return False, "Account not found."
    if str(user.get("email", "")).endswith("@demo.local"):
        return False, "Demo accounts cannot be deleted."
    if not verify_password(password, user.get("password_hash", "")):
        return False, "Password is incorrect."
    now_epoch = int(time.time())
    deleted_email = f"deleted+{uname}+{now_epoch}@deleted.local"
    with get_conn() as conn:
        user_id_row = conn.execute("SELECT id FROM users WHERE username = ?", (uname,)).fetchone()
        user_id = user_id_row["id"] if user_id_row else None
        if user_id is not None:
            conn.execute("DELETE FROM team_memberships WHERE user_id = ?", (user_id,))
        conn.execute(
            """
            UPDATE users
            SET is_active = 0, email_verified = 0, email = ?, password_hash = ?, role = 'individual'
            WHERE username = ?
            """,
            (deleted_email, hash_password(secrets.token_urlsafe(24)), uname),
        )
        conn.execute(
            "UPDATE user_sessions SET logout_at = ?, last_seen_at = ? WHERE username = ? AND logout_at IS NULL",
            (_now_utc(), _now_utc(), uname),
        )
        conn.execute(
            "UPDATE auth_tokens SET used_epoch = ? WHERE username = ? AND used_epoch IS NULL",
            (now_epoch, uname),
        )
    return True, None


def delete_user_account_by_email(email: str, password: str):
    user = _get_user_row_by_email(email)
    if not user:
        return False, "No account found for this email."
    return delete_user_account(user["username"], password)


def insert_department_record(record: dict):
    init_db()
    rec_id = record.get("id")
    if not rec_id:
        return
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO department_records (id, payload_json, owner, team, review_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                payload_json = excluded.payload_json,
                review_status = excluded.review_status
            """,
            (
                rec_id,
                json.dumps(record, ensure_ascii=True),
                record.get("owner", ""),
                record.get("team", "individual"),
                record.get("review_status", "submitted"),
                record.get("timestamp", _now_utc()),
            ),
        )


def insert_audit_event(event: dict):
    init_db()
    evt_id = event.get("id")
    if not evt_id:
        return
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO audit_events (id, event_type, actor, team, details_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO NOTHING
            """,
            (
                evt_id,
                event.get("event_type", ""),
                event.get("actor", ""),
                event.get("team", "individual"),
                json.dumps(event.get("details", {}), ensure_ascii=True),
                event.get("timestamp", _now_utc()),
            ),
        )


def migrate_collab_store():
    init_db()
    if not COLLAB_STORE_PATH.exists():
        return {"records": 0, "events": 0}
    with COLLAB_STORE_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    records = data.get("department_registry", [])
    events = data.get("audit_log", [])
    for record in records:
        insert_department_record(record)
    for event in events:
        insert_audit_event(event)
    return {"records": len(records), "events": len(events)}


def fetch_rows(query: str, params=()):
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def backend_overview():
    return {
        "users": fetch_rows("SELECT username, email, email_verified, role, is_active, created_at FROM users ORDER BY username"),
        "teams": fetch_rows("SELECT name, created_at FROM teams ORDER BY name"),
        "memberships": fetch_rows(
            """
            SELECT u.username, t.name AS team, m.is_admin, m.created_at
            FROM team_memberships m
            JOIN users u ON u.id = m.user_id
            JOIN teams t ON t.id = m.team_id
            ORDER BY t.name, u.username
            """
        ),
        "record_count": fetch_rows("SELECT COUNT(*) AS n FROM department_records")[0]["n"],
        "audit_count": fetch_rows("SELECT COUNT(*) AS n FROM audit_events")[0]["n"],
        "active_sessions": fetch_rows("SELECT COUNT(*) AS n FROM user_sessions WHERE logout_at IS NULL")[0]["n"],
        "sessions": fetch_rows(
            """
            SELECT session_id, username, login_mode, team, role, login_at, last_seen_at, logout_at
            FROM user_sessions
            ORDER BY login_at DESC
            LIMIT 200
            """
        ),
    }


def set_system_setting(key: str, value: str):
    now = _now_utc()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO system_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (key, value, now),
        )


def get_system_setting(key: str, default: str = ""):
    rows = fetch_rows("SELECT value FROM system_settings WHERE key = ?", (key,))
    return rows[0]["value"] if rows else default


def get_system_settings(prefix: str = ""):
    if prefix:
        return fetch_rows(
            "SELECT key, value, updated_at FROM system_settings WHERE key LIKE ? ORDER BY key",
            (f"{prefix}%",),
        )
    return fetch_rows("SELECT key, value, updated_at FROM system_settings ORDER BY key")


def start_user_session(username: str, login_mode: str, team: str, role: str):
    init_db()
    session_id = str(uuid4())
    now = _now_utc()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO user_sessions (session_id, username, login_mode, team, role, login_at, last_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, username, login_mode, team or "individual", role or "individual", now, now),
        )
    return session_id


def touch_user_session(session_id: str):
    if not session_id:
        return
    with get_conn() as conn:
        conn.execute("UPDATE user_sessions SET last_seen_at = ? WHERE session_id = ?", (_now_utc(), session_id))


def end_user_session(session_id: str):
    if not session_id:
        return
    now = _now_utc()
    with get_conn() as conn:
        conn.execute(
            "UPDATE user_sessions SET logout_at = ?, last_seen_at = ? WHERE session_id = ?",
            (now, now, session_id),
        )


def get_active_session(session_id: str):
    rows = fetch_rows(
        """
        SELECT session_id, username, login_mode, team, role, login_at, last_seen_at, logout_at
        FROM user_sessions
        WHERE session_id = ? AND logout_at IS NULL
        LIMIT 1
        """,
        (session_id,),
    )
    return rows[0] if rows else None
