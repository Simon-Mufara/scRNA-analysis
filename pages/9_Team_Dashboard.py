import pandas as pd
import streamlit as st

from utils.auth import get_current_user, has_role
from utils.collaboration import (
    build_model_jsonl,
    delete_user_memory,
    get_department_registry,
    get_team_feed,
    get_team_snapshots,
    get_user_memories,
    init_collaboration_state,
    publish_learning_record,
    query_audit_events,
    query_department_records,
    save_user_memory,
    share_user_memory,
    summarize_audit_events,
    summarize_department_records,
    update_learning_record_status,
    validate_learning_records,
)
from utils.styles import inject_global_css, info_card, page_header, render_nav_buttons, render_sidebar

st.set_page_config(page_title="Team Dashboard", layout="wide")
inject_global_css()
render_sidebar()

state = init_collaboration_state()
user = get_current_user()
if not user.get("team"):
    st.info("Team Dashboard is only available to users assigned to a team.")
    st.stop()
username = user["username"] or "analyst"
team = user["team"]
user_role = user["role"] or "individual"
memories = get_user_memories(username)
team_feed = get_team_feed(team)
snapshots = get_team_snapshots(team) if team else st.session_state.get("shared_snapshots", [])
department_records = get_department_registry(team)
department_summary = summarize_department_records(department_records)
audit_events = query_audit_events(team=team)
audit_summary = summarize_audit_events(audit_events)

page_header(
    "🤝",
    "Team and Organization Dashboard",
    "Shared workspace for collaborative analysis and future AI pattern learning.",
)

m1, m2, m3, m4 = st.columns(4)
with m1:
    info_card("Workspace", state["workspace_name"], "#00D4FF", "🏷️")
with m2:
    info_card("Mode", state["workspace_type"], "#A855F7", "🧭")
with m3:
    info_card("My Memories", str(len(memories)), "#51CF66", "🧠")
with m4:
    info_card("Audit Events", str(audit_summary["total"]), "#FFD43B", "📦")

st.divider()
left, right = st.columns([3, 2])

with left:
    st.markdown("### 💾 Personal Memory and Previews")
    with st.form("memory_form", clear_on_submit=True):
        memory_title = st.text_input("Memory title", placeholder="T cell exhaustion signal in sample A")
        memory_preview = st.text_area(
            "Preview notes",
            placeholder="Short summary of findings, marker genes, and interpretation.",
            height=120,
        )
        save_clicked = st.form_submit_button("Save memory", type="primary")
    if save_clicked:
        try:
            save_user_memory(username, memory_title, memory_preview)
            st.success("Memory saved.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

    if memories:
        for memory in reversed(memories):
            with st.expander(f"📝 {memory['title']} · {memory['timestamp']}", expanded=False):
                st.write(memory.get("preview") or "No preview text.")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Delete", key=f"del_{memory['id']}", use_container_width=True):
                        delete_user_memory(username, memory["id"])
                        st.rerun()
                with c2:
                    if st.button(
                        "Share with Team",
                        key=f"share_{memory['id']}",
                        use_container_width=True,
                        disabled=not bool(team),
                    ):
                        share_user_memory(username, memory["id"], team)
                        st.success("Shared with team feed.")
                        st.rerun()
    else:
        st.info("No saved memories yet.")

    st.markdown("### 📊 Shared Analysis Snapshots")
    if snapshots:
        st.dataframe(pd.DataFrame(snapshots[::-1]), use_container_width=True, hide_index=True)
    else:
        st.info("No shared snapshots yet. Use the sidebar button to share your current analysis state.")

with right:
    st.markdown("### 👥 Team Shared Feed")
    if team_feed:
        st.dataframe(pd.DataFrame(team_feed[::-1]), use_container_width=True, hide_index=True)
    elif team:
        st.info("No team memories shared yet.")
    else:
        st.info("Join a team account to use team sharing.")

    st.markdown("### 🧾 Department Learning Registry")
    with st.expander("Filter registry records", expanded=False):
        status_options = ["all"] + sorted({rec.get("review_status", "submitted") for rec in department_records})
        signal_options = ["all"] + sorted({rec.get("signal_type", "other") for rec in department_records})
        owner_options = ["all"] + sorted({rec.get("owner", "") for rec in department_records if rec.get("owner")})
        f1, f2 = st.columns(2)
        reg_status_filter = f1.selectbox("Review status", status_options, key="reg_status_filter")
        reg_signal_filter = f2.selectbox("Signal type", signal_options, key="reg_signal_filter")
        f3, f4 = st.columns(2)
        reg_owner_filter = f3.selectbox("Owner", owner_options, key="reg_owner_filter")
        reg_search = f4.text_input("Search", key="reg_search_filter", placeholder="title, summary, tag")
    filtered_records = query_department_records(
        team=team,
        review_status=reg_status_filter,
        signal_type=reg_signal_filter,
        owner=reg_owner_filter,
        search=reg_search,
    )
    st.caption(f"Showing {len(filtered_records)} of {department_summary['total']} records.")
    memory_options = {f"{m['title']} ({m['timestamp']})": m for m in memories}
    selected_label = st.selectbox(
        "Source memory",
        ["Manual entry"] + list(memory_options.keys()),
        index=0,
        key="dept_source_memory",
    )
    selected_memory = memory_options.get(selected_label)
    default_title = selected_memory["title"] if selected_memory else ""
    default_summary = selected_memory.get("preview", "") if selected_memory else ""
    with st.form("department_registry_form", clear_on_submit=True):
        reg_title = st.text_input("Result title", value=default_title, placeholder="Interferon-high myeloid signature")
        reg_summary = st.text_area(
            "Result summary",
            value=default_summary,
            placeholder="Concise, reproducible summary of finding and context.",
            height=100,
        )
        reg_signal_type = st.selectbox(
            "Signal type",
            ["cell_type_shift", "differential_expression", "pathway_activation", "clinical_association", "other"],
        )
        reg_tags = st.text_input("Tags (comma-separated)", placeholder="tcell, exhaustion, pdcd1, checkpoint")
        reg_context = st.text_input("Clinical context", placeholder="NSCLC pre-treatment biopsy")
        reg_outcome = st.selectbox("Outcome label", ["positive", "negative", "neutral", "undetermined"])
        reg_evidence = st.selectbox("Evidence level", ["validated", "replicated", "exploratory"])
        publish_clicked = st.form_submit_button("Publish to department registry", type="primary", use_container_width=True)
    if publish_clicked:
        if not has_role(user_role, "organization"):
            st.error("Publishing to department registry requires organization role access.")
        else:
            try:
                publish_learning_record(
                    username=username,
                    team=team,
                    title=reg_title,
                    summary=reg_summary,
                    signal_type=reg_signal_type,
                    tags=reg_tags,
                    clinical_context=reg_context,
                    outcome_label=reg_outcome,
                    evidence_level=reg_evidence,
                    source_kind="memory" if selected_memory else "manual",
                    source_id=selected_memory["id"] if selected_memory else "",
                )
                st.success("Published to department learning registry.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    if filtered_records:
        dept_df = pd.DataFrame(filtered_records[::-1])
        st.dataframe(dept_df, use_container_width=True, hide_index=True)
        csv_bytes = dept_df.to_csv(index=False).encode("utf-8")
        b1, b2 = st.columns(2)
        b1.download_button(
            "Export CSV",
            data=csv_bytes,
            file_name="department_learning_registry.csv",
            mime="text/csv",
            use_container_width=True,
        )
        b2.download_button(
            "Export JSON",
            data=dept_df.to_json(orient="records", indent=2),
            file_name="department_learning_registry.json",
            mime="application/json",
            use_container_width=True,
        )
    else:
        st.info("No records match current filters.")

    st.markdown("### ✅ Department Review Workflow")
    review_df = pd.DataFrame(department_records[::-1]) if department_records else pd.DataFrame()
    if not review_df.empty:
        st.dataframe(
            review_df[["id", "title", "owner", "signal_type", "review_status", "reviewed_by", "reviewed_at"]],
            use_container_width=True,
            hide_index=True,
        )
        if has_role(user_role, "organization"):
            submitted = [rec for rec in department_records if rec.get("review_status") in {"submitted", "needs_revision"}]
            options = {
                f"{rec.get('title', 'Untitled')} ({rec.get('id', '')[:8]})": rec.get("id")
                for rec in submitted
            }
            with st.form("review_action_form", clear_on_submit=True):
                selected = st.selectbox(
                    "Select record to review",
                    list(options.keys()) if options else ["No pending records"],
                    disabled=not bool(options),
                )
                decision = st.selectbox("Decision", ["approved", "rejected", "needs_revision"])
                review_comment = st.text_area("Reviewer comment", height=80, placeholder="Optional rationale")
                review_submit = st.form_submit_button("Apply review decision", use_container_width=True)
            if review_submit and options:
                try:
                    update_learning_record_status(
                        record_id=options[selected],
                        reviewer=username,
                        new_status=decision,
                        comment=review_comment,
                    )
                    st.success("Review status updated.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        else:
            st.caption("Only organization role users can approve/reject records.")
    else:
        st.info("No records available for review yet.")

    st.markdown("### 🧪 Model-ready Dataset Pipeline")
    approved_only = st.checkbox("Use approved records only", value=True, key="approved_only_export")
    records_for_model = (
        [rec for rec in department_records if rec.get("review_status") == "approved"]
        if approved_only
        else department_records
    )
    quality = validate_learning_records(records_for_model)
    q1, q2, q3 = st.columns(3)
    q1.metric("Total Records", quality["total"])
    q2.metric("Valid for Model", quality["valid"])
    q3.metric("Rejected", quality["invalid"])
    if quality["rejected"]:
        with st.expander("View rejected records", expanded=False):
            st.dataframe(pd.DataFrame(quality["rejected"]), use_container_width=True, hide_index=True)
    if quality["curated"]:
        st.download_button(
            "Export Model JSONL",
            data=build_model_jsonl(quality["curated"]),
            file_name="department_model_dataset.jsonl",
            mime="application/json",
            use_container_width=True,
        )
        st.caption("JSONL export uses structured input-target pairs for supervised model training.")
    else:
        st.info("No valid model-ready records yet. Publish records with complete fields and valid outcomes.")

    st.markdown("### 🛡️ Audit Log and Governance")
    only_mine = st.checkbox("Show only my actions", value=False, key="audit_only_mine")
    event_types = ["all"] + sorted(audit_summary["event_counts"].keys())
    event_filter = st.selectbox("Event type", event_types, key="audit_event_type")
    events = query_audit_events(team=team, actor=username if only_mine else "", event_type=event_filter)
    if audit_summary["event_counts"]:
        st.caption("Top events: " + ", ".join(f"{k}:{v}" for k, v in sorted(audit_summary["event_counts"].items())))
    if events:
        audit_df = pd.DataFrame(events[::-1])
        st.dataframe(audit_df, use_container_width=True, hide_index=True)
        a1, a2 = st.columns(2)
        a1.download_button(
            "Export Audit CSV",
            data=audit_df.to_csv(index=False).encode("utf-8"),
            file_name="team_audit_log.csv",
            mime="text/csv",
            use_container_width=True,
        )
        a2.download_button(
            "Export Audit JSON",
            data=audit_df.to_json(orient="records", indent=2),
            file_name="team_audit_log.json",
            mime="application/json",
            use_container_width=True,
        )
    else:
        st.info("No audit events yet for current scope.")

    st.markdown("### 🧠 AI Readiness")
    st.markdown(
        """
        - Department registry captures structured signals for model learning.
        - Standard fields improve training quality and reproducibility.
        - Exports can seed evaluation sets and supervision datasets.
        """
    )
    st.text_area(
        "Team Notes",
        key="team_dashboard_notes",
        placeholder="Capture recurring biological patterns, decisions, and hypotheses for your team.",
        height=170,
    )

render_nav_buttons(9)
