import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import streamlit as st

WORKSPACE_TYPES = ["Individual", "Team", "Organization"]
STORE_PATH = Path(__file__).resolve().parents[1] / "data" / "collab_store.json"
MODEL_SIGNAL_TYPES = {"cell_type_shift", "differential_expression", "pathway_activation", "clinical_association"}
MODEL_OUTCOMES = {"positive", "negative", "neutral"}


def _now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _empty_store():
    return {
        "user_memories": {},
        "team_feed": {},
        "team_snapshots": {},
        "department_registry": [],
        "private_learning": {},
        "audit_log": [],
        "presence": {},
        "shared_analysis": {},
        "annotations": [],
        "submitted_reports_team": {},
        "submitted_reports_public": [],
    }


def _load_store():
    if not STORE_PATH.exists():
        return _empty_store()
    try:
        with STORE_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return _empty_store()
    base = _empty_store()
    base.update(data if isinstance(data, dict) else {})
    return base


def _save_store(store):
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STORE_PATH.open("w", encoding="utf-8") as f:
        json.dump(store, f, indent=2)


def _append_audit_event(event_type: str, actor: str, team: str = "", details=None):
    store = _load_store()
    event = {
        "id": str(uuid4()),
        "timestamp": _now_utc(),
        "event_type": event_type,
        "actor": actor or "unknown",
        "team": team or "individual",
        "details": details or {},
    }
    store["audit_log"].append(event)
    _save_store(store)
    try:
        from utils.backend_db import insert_audit_event

        insert_audit_event(event)
    except Exception:
        pass


def init_collaboration_state():
    username = st.session_state.get("auth_username")
    team = st.session_state.get("auth_team")
    role = st.session_state.get("auth_role", "individual")

    defaults = {
        "workspace_type": "Team" if team else ("Organization" if role == "organization" else "Individual"),
        "workspace_name": team or f"{(username or 'Personal').title()} Workspace",
        "workspace_owner": username or "Analyst",
        "shared_snapshots": [],
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    return {key: st.session_state[key] for key in defaults}


def get_user_memories(username: str):
    if not username:
        return []
    store = _load_store()
    return store["user_memories"].get(username, [])


def save_user_memory(username: str, title: str, preview: str):
    if not username:
        raise ValueError("User is not logged in.")
    if not title.strip():
        raise ValueError("Memory title is required.")
    store = _load_store()
    store["user_memories"].setdefault(username, [])
    memory = {
        "id": str(uuid4()),
        "title": title.strip(),
        "preview": (preview or "").strip(),
        "timestamp": _now_utc(),
        "owner": username,
    }
    store["user_memories"][username].append(memory)
    _save_store(store)
    _append_audit_event("memory_saved", username, details={"title": memory["title"]})
    return memory


def delete_user_memory(username: str, memory_id: str):
    if not username:
        return False
    store = _load_store()
    memories = store["user_memories"].get(username, [])
    new_memories = [m for m in memories if m.get("id") != memory_id]
    if len(new_memories) == len(memories):
        return False
    store["user_memories"][username] = new_memories
    _save_store(store)
    _append_audit_event("memory_deleted", username, details={"memory_id": memory_id})
    return True


def share_user_memory(username: str, memory_id: str, team: str):
    if not username or not team:
        raise ValueError("Team sharing requires logged in team user.")
    store = _load_store()
    memories = store["user_memories"].get(username, [])
    memory = next((m for m in memories if m.get("id") == memory_id), None)
    if memory is None:
        raise ValueError("Memory not found.")
    feed_item = {
        "id": str(uuid4()),
        "shared_by": username,
        "team": team,
        "title": memory["title"],
        "preview": memory.get("preview", ""),
        "timestamp": _now_utc(),
    }
    store["team_feed"].setdefault(team, []).append(feed_item)
    _save_store(store)
    _append_audit_event("memory_shared", username, team=team, details={"memory_id": memory_id, "title": memory["title"]})
    return feed_item


def get_team_feed(team: str):
    if not team:
        return []
    store = _load_store()
    return store["team_feed"].get(team, [])


def get_team_snapshots(team: str):
    if not team:
        return []
    store = _load_store()
    return store["team_snapshots"].get(team, [])


def update_presence(username: str, team: str, page: str, status: str = "active"):
    if not username or not team:
        return
    store = _load_store()
    team_presence = store.setdefault("presence", {}).setdefault(team, {})
    team_presence[username] = {
        "user": username,
        "team": team,
        "page": (page or "dashboard").strip().lower(),
        "status": (status or "active").strip().lower(),
        "timestamp": _now_utc(),
        "heartbeat_epoch": int(datetime.now(timezone.utc).timestamp()),
    }
    _save_store(store)


def get_team_presence(team: str, active_within_seconds: int = 180):
    if not team:
        return []
    now_epoch = int(datetime.now(timezone.utc).timestamp())
    store = _load_store()
    items = list(store.get("presence", {}).get(team, {}).values())
    active = [item for item in items if now_epoch - int(item.get("heartbeat_epoch", 0)) <= active_within_seconds]
    return sorted(active, key=lambda x: (x.get("status", "active"), x.get("user", "")))


def share_analysis_state(username: str, team: str, state: dict):
    if not username or not team:
        raise ValueError("Team analysis sync requires a team user.")
    payload = {
        "id": str(uuid4()),
        "team": team,
        "sender": username,
        "timestamp": _now_utc(),
        "state": state or {},
    }
    store = _load_store()
    store.setdefault("shared_analysis", {})[team] = payload
    _save_store(store)
    _append_audit_event("analysis_state_shared", username, team=team, details={"keys": sorted((state or {}).keys())})
    return payload


def get_latest_shared_analysis_state(team: str):
    if not team:
        return None
    store = _load_store()
    return store.get("shared_analysis", {}).get(team)


def add_plot_annotation(username: str, team: str, plot_type: str, plot_x: float, plot_y: float, comment: str):
    if not username or not team:
        raise ValueError("Annotations require a team user.")
    text = (comment or "").strip()
    if not text:
        raise ValueError("Annotation comment is required.")
    annotation = {
        "id": str(uuid4()),
        "team": team,
        "plot_type": (plot_type or "umap").strip().lower(),
        "plot_x": float(plot_x),
        "plot_y": float(plot_y),
        "comment": text,
        "author": username,
        "timestamp": _now_utc(),
    }
    store = _load_store()
    store.setdefault("annotations", []).append(annotation)
    _save_store(store)
    _append_audit_event(
        "annotation_added",
        username,
        team=team,
        details={"annotation_id": annotation["id"], "plot_type": annotation["plot_type"]},
    )
    return annotation


def get_plot_annotations(team: str, plot_type: str = "all"):
    if not team:
        return []
    ptype = (plot_type or "all").strip().lower()
    store = _load_store()
    rows = [a for a in store.get("annotations", []) if a.get("team") == team]
    if ptype != "all":
        rows = [a for a in rows if a.get("plot_type") == ptype]
    return rows


def submit_clinical_report(username: str, team: str, report_payload: dict, visibility: str = "team"):
    if not username:
        raise ValueError("User is not logged in.")
    payload = {
        "id": str(uuid4()),
        "timestamp": _now_utc(),
        "submitted_by": username,
        "team": team or "individual",
        "visibility": (visibility or "team").strip().lower(),
        "report": report_payload or {},
    }
    store = _load_store()
    # Always keep an immutable record in public archive for governance/model traceability.
    store.setdefault("submitted_reports_public", []).append(payload)
    if payload["visibility"] != "public":
        t = payload["team"]
        store.setdefault("submitted_reports_team", {}).setdefault(t, []).append(payload)
    _save_store(store)
    _append_audit_event(
        "clinical_report_submitted",
        username,
        team=payload["team"],
        details={"report_id": payload["id"], "visibility": payload["visibility"]},
    )
    return payload


def get_submitted_clinical_reports(team: str = "", visibility: str = "team"):
    store = _load_store()
    vis = (visibility or "team").strip().lower()
    if vis == "public":
        return store.get("submitted_reports_public", [])
    if not team:
        return []
    return store.get("submitted_reports_team", {}).get(team, [])


def capture_pipeline_training_record(username: str, team: str, payload: dict):
    data = payload or {}
    required = data.get("required_steps_complete", False)
    if not required:
        return None
    return submit_clinical_report(
        username=username,
        team=team,
        report_payload={
            "record_type": "pipeline_training_capture",
            **data,
        },
        visibility="public",
    )


def publish_learning_record(
    username: str,
    team: str,
    title: str,
    summary: str,
    signal_type: str,
    tags: str,
    clinical_context: str,
    outcome_label: str,
    evidence_level: str,
    source_kind: str = "manual",
    source_id: str = "",
):
    if not username:
        raise ValueError("User is not logged in.")
    if not title.strip():
        raise ValueError("Result title is required.")

    tags_clean = [tag.strip().lower() for tag in (tags or "").split(",") if tag.strip()]
    record = {
        "id": str(uuid4()),
        "timestamp": _now_utc(),
        "owner": username,
        "team": team or "individual",
        "title": title.strip(),
        "summary": (summary or "").strip(),
        "signal_type": (signal_type or "other").strip().lower(),
        "tags": tags_clean,
        "clinical_context": (clinical_context or "").strip(),
        "outcome_label": (outcome_label or "undetermined").strip().lower(),
        "evidence_level": (evidence_level or "exploratory").strip().lower(),
        "source_kind": (source_kind or "manual").strip().lower(),
        "source_id": (source_id or "").strip(),
        "review_status": "submitted",
        "reviewed_by": "",
        "review_comment": "",
        "reviewed_at": "",
    }
    store = _load_store()
    store["department_registry"].append(record)
    _save_store(store)
    try:
        from utils.backend_db import insert_department_record

        insert_department_record(record)
    except Exception:
        pass
    _append_audit_event(
        "learning_record_published",
        username,
        team=team,
        details={"record_id": record["id"], "title": record["title"], "signal_type": record["signal_type"]},
    )
    return record


def get_department_registry(team: str = ""):
    store = _load_store()
    records = store["department_registry"]
    if team:
        return [record for record in records if record.get("team") in {team, "organization"}]
    return records


def query_department_records(team: str = "", review_status: str = "all", signal_type: str = "all", owner: str = "all", search: str = ""):
    records = get_department_registry(team)
    status = (review_status or "all").strip().lower()
    signal = (signal_type or "all").strip().lower()
    owner_filter = (owner or "all").strip().lower()
    search_text = (search or "").strip().lower()

    def _match(record):
        if status != "all" and str(record.get("review_status", "")).lower() != status:
            return False
        if signal != "all" and str(record.get("signal_type", "")).lower() != signal:
            return False
        if owner_filter != "all" and str(record.get("owner", "")).lower() != owner_filter:
            return False
        if search_text:
            blob = " ".join(
                [
                    str(record.get("title", "")),
                    str(record.get("summary", "")),
                    str(record.get("clinical_context", "")),
                    ",".join(record.get("tags", [])),
                ]
            ).lower()
            return search_text in blob
        return True

    return [record for record in records if _match(record)]


def summarize_department_records(records):
    status_counts = {}
    signal_counts = {}
    for record in records:
        status = str(record.get("review_status", "unknown")).lower()
        signal = str(record.get("signal_type", "unknown")).lower()
        status_counts[status] = status_counts.get(status, 0) + 1
        signal_counts[signal] = signal_counts.get(signal, 0) + 1
    return {"total": len(records), "status_counts": status_counts, "signal_counts": signal_counts}


def update_learning_record_status(record_id: str, reviewer: str, new_status: str, comment: str = ""):
    allowed = {"submitted", "approved", "rejected", "needs_revision"}
    status = (new_status or "").strip().lower()
    if status not in allowed:
        raise ValueError("Invalid review status.")
    store = _load_store()
    records = store["department_registry"]
    idx = next((i for i, rec in enumerate(records) if rec.get("id") == record_id), None)
    if idx is None:
        raise ValueError("Record not found.")
    records[idx]["review_status"] = status
    records[idx]["reviewed_by"] = reviewer or ""
    records[idx]["review_comment"] = (comment or "").strip()
    records[idx]["reviewed_at"] = _now_utc()
    _save_store(store)
    _append_audit_event(
        "learning_record_reviewed",
        reviewer,
        team=records[idx].get("team", ""),
        details={"record_id": record_id, "status": status},
    )
    return records[idx]


def get_audit_log(team: str = "", actor: str = ""):
    store = _load_store()
    events = store["audit_log"]
    if team:
        events = [event for event in events if event.get("team") in {team, "organization", "individual"}]
    if actor:
        events = [event for event in events if event.get("actor") == actor]
    return events


def query_audit_events(team: str = "", actor: str = "", event_type: str = "all"):
    events = get_audit_log(team=team, actor=actor)
    event_filter = (event_type or "all").strip().lower()
    if event_filter == "all":
        return events
    return [event for event in events if str(event.get("event_type", "")).lower() == event_filter]


def summarize_audit_events(events):
    event_counts = {}
    for event in events:
        e_type = str(event.get("event_type", "unknown")).lower()
        event_counts[e_type] = event_counts.get(e_type, 0) + 1
    return {"total": len(events), "event_counts": event_counts}


def validate_learning_records(records):
    curated = []
    rejected = []
    for record in records:
        missing = [k for k in ("title", "summary", "signal_type", "outcome_label") if not str(record.get(k, "")).strip()]
        signal = str(record.get("signal_type", "")).strip().lower()
        outcome = str(record.get("outcome_label", "")).strip().lower()
        if missing or signal not in MODEL_SIGNAL_TYPES or outcome not in MODEL_OUTCOMES:
            rejected.append(
                {
                    "id": record.get("id"),
                    "title": record.get("title", ""),
                    "reason": "missing fields" if missing else "invalid signal/outcome",
                }
            )
            continue
        curated.append(record)
    return {
        "curated": curated,
        "rejected": rejected,
        "total": len(records),
        "valid": len(curated),
        "invalid": len(rejected),
    }


def build_model_jsonl(records):
    lines = []
    for record in records:
        payload = {
            "input": (
                f"Team: {record.get('team', '')}\n"
                f"Signal Type: {record.get('signal_type', '')}\n"
                f"Clinical Context: {record.get('clinical_context', '')}\n"
                f"Summary: {record.get('summary', '')}\n"
                f"Tags: {', '.join(record.get('tags', []))}"
            ),
            "target": record.get("outcome_label", ""),
            "metadata": {
                "id": record.get("id", ""),
                "owner": record.get("owner", ""),
                "timestamp": record.get("timestamp", ""),
                "evidence_level": record.get("evidence_level", ""),
                "title": record.get("title", ""),
            },
        }
        lines.append(json.dumps(payload, ensure_ascii=True))
    return "\n".join(lines)


def log_private_learning(username: str, done_steps):
    if not username:
        return
    store = _load_store()
    entries = store["private_learning"].setdefault(username, [])
    entries.append(
        {
            "id": str(uuid4()),
            "timestamp": _now_utc(),
            "done_steps": list(done_steps),
            "completion": len(done_steps),
        }
    )
    _save_store(store)
    _append_audit_event("private_learning_logged", username, details={"completion": len(done_steps)})


def add_shared_snapshot():
    adata = st.session_state.get("adata")
    if adata is None:
        raise ValueError("No dataset loaded for sharing.")

    team = st.session_state.get("auth_team")
    owner = st.session_state.get("auth_username", "analyst")
    snapshot = {
        "id": str(uuid4()),
        "timestamp": _now_utc(),
        "owner": owner,
        "workspace": st.session_state.get("workspace_name", "Shared Workspace") or "Shared Workspace",
        "cells": int(adata.n_obs),
        "genes": int(adata.n_vars),
        "clusters": int(adata.obs["leiden"].nunique()) if "leiden" in adata.obs.columns else 0,
        "cell_types": int(adata.obs["cell_type"].nunique()) if "cell_type" in adata.obs.columns else 0,
    }

    if team:
        store = _load_store()
        store["team_snapshots"].setdefault(team, []).append(snapshot)
        _save_store(store)
        st.session_state["shared_snapshots"] = store["team_snapshots"].get(team, [])
        _append_audit_event("snapshot_shared", owner, team=team, details={"snapshot_id": snapshot["id"]})
    else:
        snapshots = st.session_state.get("shared_snapshots", [])
        snapshots.append(snapshot)
        st.session_state["shared_snapshots"] = snapshots
        _append_audit_event("snapshot_saved_individual", owner, details={"snapshot_id": snapshot["id"]})
    return snapshot
