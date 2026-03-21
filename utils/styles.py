"""Shared CSS/styling injected into every page."""
import streamlit as st

from utils.auth import get_current_user, logout_user, render_login_gate
from utils.collaboration import add_shared_snapshot, get_team_snapshots, init_collaboration_state, log_private_learning

PLOTLY_TEMPLATE = "plotly_dark"

PALETTE = [
    "#00D4FF", "#7B2FBE", "#FF6B6B", "#51CF66", "#FFD43B",
    "#FF922B", "#74C0FC", "#F783AC", "#A9E34B", "#63E6BE",
    "#E599F7", "#FFA94D", "#4DABF7", "#FF8787", "#66D9E8",
]

def inject_global_css():
    theme_mode = st.session_state.get("theme_mode", "Dark")
    if theme_mode == "Light":
        st.markdown(
            """
            <style>
            :root {
                --bg: #F7F9FC;
                --surface: #FFFFFF;
                --surface-2: #F3F6FB;
                --border: #D9E2EC;
                --text: #0F172A;
                --muted: #475569;
                --accent: #0284C7;
                --accent-soft: #E0F2FE;
            }
            [data-testid="stAppViewContainer"] { background: var(--bg) !important; }
            [data-testid="stMain"] { background: transparent !important; }
            [data-testid="stSidebar"] { background: var(--surface) !important; border-right: 1px solid var(--border) !important; }
            [data-testid="stSidebarContent"] { background: var(--surface) !important; }
            [data-testid="stHeader"] {
                background: #F8FAFC !important;
                border-bottom: 1px solid var(--border) !important;
            }
            [data-testid="stHeader"] * {
                color: #0F172A !important;
            }
            .block-container { max-width: 1380px !important; color: var(--text) !important; }
            [data-testid="stSidebarNavItems"] a {
                color: #334155 !important;
                border: 1px solid transparent !important;
                border-radius: 8px !important;
            }
            [data-testid="stSidebarNavItems"] a:hover {
                background: #EFF6FF !important;
                color: #0F172A !important;
                border-color: #BFDBFE !important;
            }
            [data-testid="stSidebarNavItems"] a[aria-current="page"] {
                background: #E0F2FE !important;
                color: #0369A1 !important;
                border-color: #7DD3FC !important;
                font-weight: 700 !important;
            }

            h1, h2, h3, h4, h5, h6, p, span, label, div { color: var(--text) !important; }
            small, .caption, [data-testid="stCaptionContainer"], [data-testid="stMarkdownContainer"] p { color: var(--muted) !important; }

            [data-testid="metric-container"] {
                background: var(--surface) !important;
                border: 1px solid var(--border) !important;
                box-shadow: 0 2px 12px rgba(15, 23, 42, 0.05) !important;
            }
            [data-testid="stMetricValue"] { color: var(--accent) !important; }
            [data-testid="stMetricLabel"] { color: var(--muted) !important; }

            [data-testid="stDataFrame"] {
                border: 1px solid var(--border) !important;
                background: var(--surface) !important;
            }

            [data-testid="baseButton-primary"] {
                background: linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%) !important;
                color: #FFFFFF !important;
                border: none !important;
            }
            [data-testid="baseButton-secondary"] {
                background: var(--surface) !important;
                color: var(--accent) !important;
                border: 1px solid #93C5FD !important;
            }

            [data-testid="stTabs"] [data-baseweb="tab-list"] {
                border-bottom: 1px solid var(--border) !important;
            }
            [data-testid="stTabs"] [data-baseweb="tab"] {
                color: var(--muted) !important;
                background: transparent !important;
            }
            [data-testid="stTabs"] [aria-selected="true"] {
                color: var(--accent) !important;
                border-bottom: 2px solid var(--accent) !important;
                background: transparent !important;
            }

            [data-testid="stTextInput"] input,
            [data-testid="stTextArea"] textarea,
            [data-testid="stNumberInput"] input,
            [data-testid="stSelectbox"] > div > div {
                background: var(--surface) !important;
                color: var(--text) !important;
                border: 1px solid var(--border) !important;
            }
            [data-testid="stTextInput"] input::placeholder,
            [data-testid="stTextArea"] textarea::placeholder {
                color: #94A3B8 !important;
            }
            [data-testid="stTextInput"] input:focus,
            [data-testid="stTextArea"] textarea:focus,
            [data-testid="stNumberInput"] input:focus {
                border-color: var(--accent) !important;
                box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.18) !important;
            }

            [data-testid="stFileUploader"] section {
                background: var(--surface-2) !important;
                border: 2px dashed #B6C2CF !important;
            }
            [data-testid="stExpander"] {
                background: var(--surface) !important;
                border: 1px solid var(--border) !important;
            }
            [data-testid="stAlert"] {
                background: #F8FAFC !important;
                border: 1px solid var(--border) !important;
            }
            /* Light-theme rescue for hard-coded dark inline cards/text */
            div[style*="background:#0D1117"],
            div[style*="background:rgba(13,17,23"],
            div[style*="background:rgba(22,27,34"] {
                background: #FFFFFF !important;
                border-color: #D9E2EC !important;
            }
            div[style*="color:#E6EDF3"],
            div[style*="color:#C9D1D9"],
            div[style*="color:#8B949E"],
            div[style*="color:#6E7681"],
            span[style*="color:#E6EDF3"],
            span[style*="color:#C9D1D9"],
            span[style*="color:#8B949E"],
            span[style*="color:#6E7681"],
            p[style*="color:#E6EDF3"],
            p[style*="color:#C9D1D9"],
            p[style*="color:#8B949E"],
            p[style*="color:#6E7681"] {
                color: #1E293B !important;
            }

            code {
                background: #EEF2FF !important;
                color: #1D4ED8 !important;
                border: 1px solid #C7D2FE !important;
            }
            hr { border-color: var(--border) !important; }
            </style>
            """,
            unsafe_allow_html=True,
        )
        return
    st.markdown("""
    <style>
    /* ── Google Fonts – Inter ─────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    }

    /* Keep Streamlit/material icons rendering as icons (not plain text ligatures). */
    .material-icons,
    .material-symbols-rounded,
    .material-symbols-outlined,
    .material-symbols-sharp {
        font-family: 'Material Symbols Rounded', 'Material Icons' !important;
        font-weight: normal !important;
        font-style: normal !important;
        line-height: 1 !important;
        letter-spacing: normal !important;
        text-transform: none !important;
        white-space: nowrap !important;
        word-wrap: normal !important;
        direction: ltr !important;
        -webkit-font-smoothing: antialiased !important;
    }

    /* ── Scrollbar ───────────────────────────── */
    ::-webkit-scrollbar { width: 4px; height: 4px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #30363D; border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(0,212,255,0.4); }

    /* ── App background ──────────────────────── */
    [data-testid="stAppViewContainer"] {
        background: #070B14;
    }
    [data-testid="stMain"] { background: transparent; }
    .block-container {
        padding-top: 1.8rem !important;
        padding-bottom: 3rem !important;
        max-width: 1380px !important;
    }

    /* ── Sidebar ─────────────────────────────── */
    [data-testid="stSidebar"] {
        background: #0D1117 !important;
        border-right: 1px solid #161B22 !important;
    }
    [data-testid="stSidebarContent"] { padding: 0 !important; }

    /* Sidebar nav items */
    [data-testid="stSidebarNavItems"] { padding: 4px 8px !important; }
    [data-testid="stSidebarNavItems"] a {
        border-radius: 8px !important;
        margin: 2px 0 !important;
        padding: 8px 12px !important;
        color: #A1ABB8 !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        letter-spacing: -0.01em !important;
        transition: all 0.15s ease !important;
        border: 1px solid transparent !important;
        display: block !important;
    }
    [data-testid="stSidebarNavItems"] a:hover {
        background: rgba(0,212,255,0.06) !important;
        color: #E6EDF3 !important;
        border-color: rgba(0,212,255,0.12) !important;
    }
    [data-testid="stSidebarNavItems"] a[aria-current="page"] {
        background: rgba(0,212,255,0.09) !important;
        color: #00D4FF !important;
        border-color: rgba(0,212,255,0.22) !important;
        font-weight: 600 !important;
    }

    /* ── Headings ────────────────────────────── */
    h1 {
        background: linear-gradient(135deg, #FFFFFF 0%, #00D4FF 55%, #A855F7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.04em !important;
        line-height: 1.2 !important;
    }
    h2 {
        color: #E6EDF3 !important;
        font-weight: 700 !important;
        letter-spacing: -0.025em !important;
        font-size: 1.35rem !important;
    }
    h3 {
        color: #C9D1D9 !important;
        font-weight: 600 !important;
        letter-spacing: -0.01em !important;
        font-size: 1rem !important;
    }

    /* ── Metric cards ────────────────────────── */
    [data-testid="metric-container"] {
        background: rgba(22,27,34,0.7) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid #21262D !important;
        border-radius: 14px !important;
        padding: 18px 22px !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="metric-container"]:hover {
        border-color: rgba(0,212,255,0.35) !important;
        box-shadow: 0 0 0 1px rgba(0,212,255,0.08), 0 12px 40px rgba(0,0,0,0.5) !important;
        transform: translateY(-2px) !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #00D4FF !important;
        letter-spacing: -0.03em !important;
    }
    [data-testid="stMetricLabel"] {
        color: #9AA4AF !important;
        font-size: 0.75rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        font-weight: 500 !important;
    }

    /* ── DataFrames ──────────────────────────── */
    [data-testid="stDataFrame"] {
        border-radius: 12px !important;
        border: 1px solid #21262D !important;
        overflow: hidden !important;
    }

    /* ── Buttons ─────────────────────────────── */
    [data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #00D4FF 0%, #0099BB 100%) !important;
        color: #0B1220 !important;
        font-weight: 700 !important;
        font-size: 0.875rem !important;
        letter-spacing: -0.01em !important;
        border: none !important;
        border-radius: 9px !important;
        padding: 10px 20px !important;
        transition: all 0.15s ease !important;
    }
    [data-testid="baseButton-primary"]:hover {
        background: linear-gradient(135deg, #33DDFF 0%, #00BDD4 100%) !important;
        box-shadow: 0 0 24px rgba(0,212,255,0.35), 0 4px 16px rgba(0,0,0,0.4) !important;
        transform: translateY(-1px) !important;
    }
    [data-testid="baseButton-secondary"] {
        background: transparent !important;
        border: 1px solid rgba(0,212,255,0.4) !important;
        color: #00D4FF !important;
        border-radius: 9px !important;
        font-weight: 600 !important;
        font-size: 0.875rem !important;
        transition: all 0.15s ease !important;
    }
    [data-testid="baseButton-secondary"]:hover {
        background: rgba(0,212,255,0.08) !important;
        border-color: #00D4FF !important;
    }

    /* ── Tabs ────────────────────────────────── */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        background: transparent !important;
        border-bottom: 1px solid #21262D !important;
        gap: 0 !important;
        padding: 0 !important;
    }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        color: #A9B2BD !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        padding: 10px 18px !important;
        border-radius: 0 !important;
        border-bottom: 2px solid transparent !important;
        margin-bottom: -1px !important;
        background: transparent !important;
        transition: all 0.15s !important;
        letter-spacing: -0.01em !important;
    }
    [data-testid="stTabs"] [data-baseweb="tab"]:hover {
        color: #C9D1D9 !important;
        background: transparent !important;
    }
    [data-testid="stTabs"] [aria-selected="true"] {
        color: #E6EDF3 !important;
        border-bottom: 2px solid #00D4FF !important;
        background: transparent !important;
        font-weight: 600 !important;
    }

    /* ── Alert / Info boxes ──────────────────── */
    [data-testid="stAlert"] {
        border-radius: 10px !important;
        border-left-width: 3px !important;
        backdrop-filter: blur(8px) !important;
        font-size: 0.875rem !important;
    }

    /* ── Inputs ──────────────────────────────── */
    [data-testid="stNumberInput"] input,
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {
        background: #0D1117 !important;
        border: 1px solid #30363D !important;
        border-radius: 8px !important;
        color: #E6EDF3 !important;
        font-size: 0.875rem !important;
        transition: border-color 0.15s !important;
    }
    [data-testid="stNumberInput"] input:focus,
    [data-testid="stTextInput"] input:focus,
    [data-testid="stTextArea"] textarea:focus {
        border-color: #00D4FF !important;
        box-shadow: 0 0 0 3px rgba(0,212,255,0.1) !important;
        outline: none !important;
    }

    /* ── Selectbox ───────────────────────────── */
    [data-testid="stSelectbox"] > div > div {
        background: #0D1117 !important;
        border: 1px solid #30363D !important;
        border-radius: 8px !important;
        font-size: 0.875rem !important;
    }

    /* ── Multiselect tags ────────────────────── */
    [data-testid="stMultiSelect"] span[data-baseweb="tag"] {
        background: rgba(0,212,255,0.1) !important;
        border: 1px solid rgba(0,212,255,0.3) !important;
        border-radius: 6px !important;
        color: #00D4FF !important;
        font-size: 0.78rem !important;
    }

    /* ── File uploader ───────────────────────── */
    [data-testid="stFileUploader"] section {
        border: 2px dashed #30363D !important;
        border-radius: 14px !important;
        background: rgba(13,17,23,0.6) !important;
        transition: border-color 0.2s, background 0.2s !important;
        padding: 32px !important;
    }
    [data-testid="stFileUploader"] section:hover {
        border-color: rgba(0,212,255,0.5) !important;
        background: rgba(0,212,255,0.02) !important;
    }

    /* ── Slider ──────────────────────────────── */
    [data-testid="stSlider"] [role="slider"] {
        background: #00D4FF !important;
        border: 2px solid #0D1117 !important;
        box-shadow: 0 0 0 2px #00D4FF !important;
    }
    [data-testid="stSlider"] div[data-testid="stTickBar"] + div div {
        background: linear-gradient(90deg, #00D4FF, #7B2FBE) !important;
    }

    /* ── Progress bar ────────────────────────── */
    [data-testid="stProgress"] > div > div {
        background: linear-gradient(90deg, #00D4FF, #7B2FBE) !important;
        border-radius: 10px !important;
    }

    /* ── Expander ────────────────────────────── */
    [data-testid="stExpander"] {
        border: 1px solid #21262D !important;
        border-radius: 12px !important;
        background: rgba(22,27,34,0.4) !important;
    }
    [data-testid="stExpander"]:hover {
        border-color: rgba(0,212,255,0.2) !important;
    }

    /* ── Code blocks ─────────────────────────── */
    code {
        background: rgba(110,118,129,0.1) !important;
        border: 1px solid rgba(110,118,129,0.2) !important;
        border-radius: 5px !important;
        padding: 2px 6px !important;
        font-size: 0.83em !important;
        color: #79C0FF !important;
    }

    /* ── Divider ─────────────────────────────── */
    hr { border-color: #21262D !important; margin: 1.5rem 0 !important; }

    /* ── Spinner ─────────────────────────────── */
    .stSpinner > div > div { border-top-color: #00D4FF !important; }

    /* ── Radio / Checkbox labels ─────────────── */
    [data-testid="stRadio"] label,
    [data-testid="stCheckbox"] label {
        color: #C9D1D9 !important;
        font-size: 0.875rem !important;
        letter-spacing: -0.01em !important;
    }

    /* ── Tooltip ─────────────────────────────── */
    [data-testid="stTooltipHoverTarget"] { color: #6E7681 !important; }

    /* ── Success / warning / error ───────────── */
    .stSuccess { border-left-color: #51CF66 !important; }
    .stWarning { border-left-color: #FFD43B !important; }
    .stError   { border-left-color: #FF6B6B !important; }
    .stInfo    { border-left-color: #00D4FF !important; }
    </style>
    """, unsafe_allow_html=True)


def render_sidebar():
    """Inject branded sidebar header + pipeline progress — call once per page."""
    render_login_gate()
    init_collaboration_state()
    user = get_current_user()
    try:
        from utils.backend_db import touch_user_session

        now_ts = __import__("time").time()
        last_touch = float(st.session_state.get("_last_session_touch_ts", 0.0) or 0.0)
        # Reduce DB writes on frequent reruns; still keeps active sessions fresh.
        if now_ts - last_touch >= 30:
            touch_user_session(user.get("session_id"))
            st.session_state["_last_session_touch_ts"] = now_ts
    except Exception:
        pass
    completed = st.session_state.get("pipeline_status", {})
    st.session_state.setdefault("theme_mode", "Dark")
    lucide_base = "https://unpkg.com/lucide-static@latest/icons"
    icon_map = {
        "upload_file": "upload",
        "biotech": "microscope",
        "monitoring": "chart-scatter",
        "sell": "tags",
        "search": "search",
        "query_stats": "line-chart",
        "route": "route",
        "description": "file-text",
        "logo": "dna",
    }
    pipeline_steps = [
        ("Upload",           "upload_file"),
        ("QC",               "biotech"),
        ("Clustering",       "monitoring"),
        ("Annotation",       "sell"),
        ("Gene Explorer",    "search"),
        ("Diff. Expression", "query_stats"),
        ("Pathway",          "route"),
        ("Report",           "description"),
    ]
    done_steps = [step for step, _ in pipeline_steps if completed.get(step) == "done"]
    total_steps = len(pipeline_steps)
    progress_pct = int((len(done_steps) / total_steps) * 100)
    seen_key = "_pipeline_done_steps_seen"
    if seen_key not in st.session_state:
        st.session_state[seen_key] = done_steps.copy()
    else:
        newly_done = [step for step in done_steps if step not in st.session_state[seen_key]]
        if newly_done:
            alert = f"Pipeline update: {', '.join(newly_done)} completed ({progress_pct}%)."
            if hasattr(st, "toast"):
                st.toast(alert, icon="✅")
            else:
                st.sidebar.success(alert)
            log_private_learning(user.get("username"), done_steps)
        st.session_state[seen_key] = done_steps.copy()

    sidebar_html = (
        '<div style="padding:16px 14px 0;">'
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">'
        '<div style="background:linear-gradient(135deg,rgba(0,212,255,0.15),rgba(123,47,190,0.15));'
        'border:1px solid rgba(0,212,255,0.25);border-radius:10px;width:36px;height:36px;'
        'display:flex;align-items:center;justify-content:center;font-size:1.1rem;flex-shrink:0;">'
        f'<img src="{lucide_base}/{icon_map["logo"]}.svg" width="18" height="18" style="filter:invert(68%) sepia(71%) saturate(2964%) hue-rotate(150deg) brightness(100%) contrast(101%);" /></div>'
        '<div>'
        '<div style="color:#E6EDF3;font-weight:700;font-size:0.88rem;letter-spacing:-0.02em;line-height:1.2;">SingleCell Explorer</div>'
        '<div style="color:#6E7681;font-size:0.7rem;">Clinical &amp; Research Platform</div>'
        '</div></div>'
        '<div style="display:flex;gap:5px;margin-bottom:14px;">'
        '<span style="background:rgba(81,207,102,0.1);color:#51CF66;border:1px solid rgba(81,207,102,0.3);border-radius:20px;padding:2px 8px;font-size:0.67rem;font-weight:600;">● LIVE</span>'
        '<span style="background:rgba(0,212,255,0.06);color:#6E7681;border:1px solid #21262D;border-radius:20px;padding:2px 8px;font-size:0.67rem;">v1.0.0</span>'
        '</div>'
        '<div style="border-top:1px solid #21262D;padding-top:12px;margin-bottom:4px;">'
        '<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">'
        '<div style="color:#6E7681;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.1em;font-weight:600;">Pipeline</div>'
        f'<div style="color:#C9D1D9;font-size:0.74rem;font-weight:600;">{len(done_steps)}/{total_steps}</div>'
        '</div>'
        '</div></div>'
        '<div style="border-top:1px solid #161B22;margin-top:8px;padding-top:6px;"></div>'
    )
    st.sidebar.markdown(sidebar_html, unsafe_allow_html=True)
    theme_choice = st.sidebar.selectbox("Theme", ["Dark", "Light"], index=0 if st.session_state.get("theme_mode") == "Dark" else 1)
    if theme_choice != st.session_state.get("theme_mode"):
        st.session_state["theme_mode"] = theme_choice
        try:
            st.query_params["theme_mode"] = theme_choice
        except Exception:
            pass
        st.rerun()
    st.sidebar.progress(progress_pct / 100.0, text=f"Progress {progress_pct}%")
    with st.sidebar.expander("Debug Panel", expanded=False):
        loaded_size_mb = st.session_state.get("loaded_file_size_mb")
        adata = st.session_state.get("adata")
        n_cells = int(getattr(adata, "n_obs", 0)) if adata is not None else 0
        completed_steps = len(done_steps)
        st.markdown(f"- File size: {f'{loaded_size_mb:,.1f} MB' if isinstance(loaded_size_mb, (int, float)) else 'N/A'}")
        st.markdown(f"- Number of cells: {n_cells:,}")
        st.markdown(f"- Pipeline steps completed: {completed_steps}/{total_steps}")
    with st.sidebar.expander("View pipeline steps", expanded=False):
        for step, icon_name in pipeline_steps:
            is_done = completed.get(step) == "done"
            lucide_name = icon_map.get(icon_name, "circle")
            st.markdown(
                f"{'✅' if is_done else '◯'} "
                f"<img src='{lucide_base}/{lucide_name}.svg' width='14' height='14' "
                f"style='vertical-align:middle;filter:invert(60%);margin-right:2px;'/> "
                f"<span style='color:{'#51CF66' if is_done else '#6E7681'}'>{step}</span>",
                unsafe_allow_html=True,
            )
    st.sidebar.markdown(
        f"<div style='padding:0 14px 8px;color:#6E7681;font-size:0.74rem;'>"
        f"Signed in as <span style='color:#C9D1D9;font-weight:600;'>{user['username']}</span>"
        f"{' · ' + user['team'] if user['team'] else ''}<br/>"
        f"<span style='color:#8B949E;'>"
        f"{'Demo' if user.get('is_demo') else ('Entra' if user.get('login_mode') == 'Entra' else 'Registered')} account"
        f"{' · ' + user.get('email') if user.get('email') else ''}"
        f"</span></div>",
        unsafe_allow_html=True,
    )
    with st.sidebar.expander("Account settings", expanded=False):
        if st.button("Save login details on this device", key="save_login_details_btn", use_container_width=True):
            try:
                st.query_params["remember_user"] = user["username"] or ""
                st.query_params["remember_mode"] = "Team" if user.get("team") else "Individual"
                if user.get("team"):
                    st.query_params["remember_team"] = user["team"]
                elif st.query_params.get("remember_team"):
                    del st.query_params["remember_team"]
                st.success("Login details saved.")
            except Exception:
                st.error("Could not save login details.")
        if user.get("is_demo"):
            st.caption("Demo accounts cannot be deleted.")
        elif user.get("login_mode") == "Entra":
            st.caption("This account is managed by Microsoft Entra ID.")
        else:
            with st.form("delete_account_form", clear_on_submit=True):
                confirm_user = st.text_input("Confirm username")
                confirm_password = st.text_input("Confirm password", type="password")
                delete_submit = st.form_submit_button(
                    "Delete my account",
                    type="secondary",
                    use_container_width=True,
                )
            if delete_submit:
                if (confirm_user or "").strip().lower() != (user.get("username") or "").strip().lower():
                    st.error("Username confirmation does not match.")
                elif not confirm_password:
                    st.error("Password confirmation is required.")
                else:
                    try:
                        from utils.backend_db import delete_user_account

                        ok, err = delete_user_account(user.get("username"), confirm_password)
                    except Exception:
                        ok, err = False, "Account deletion failed."
                    if ok:
                        st.success("Your account has been deleted.")
                        logout_user()
                        st.switch_page("app.py")
                    else:
                        st.error(err or "Account deletion failed.")
    if user.get("team"):
        with st.sidebar.expander("Collaboration Workspace", expanded=False):
            st.text_input("Workspace Name", key="workspace_name")
            st.text_input("Your Name", key="workspace_owner")
            shared_count = len(get_team_snapshots(user["team"]))
            st.caption(f"Shared snapshots: {shared_count}")
            if st.button("Share current analysis snapshot", key="share_snapshot", use_container_width=True):
                if st.session_state.get("adata") is None:
                    st.warning("Load and analyze a dataset before sharing a snapshot.")
                else:
                    snapshot = add_shared_snapshot()
                    st.success(f"Snapshot shared at {snapshot['timestamp']}.")
    if st.sidebar.button("Logout", key="logout_btn", use_container_width=True):
        logout_user()
        st.switch_page("app.py")


def page_header(icon: str, title: str, subtitle: str = ""):
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, rgba(0,212,255,0.07) 0%, rgba(123,47,190,0.07) 100%);
        border: 1px solid rgba(0,212,255,0.18);
        border-radius: 16px;
        padding: 26px 32px;
        margin-bottom: 24px;
        position: relative;
        overflow: hidden;
    ">
        <div style="
            position:absolute;top:-60px;right:-60px;width:250px;height:250px;
            background:radial-gradient(circle,rgba(0,212,255,0.08) 0%,transparent 65%);
            border-radius:50%;pointer-events:none;
        "></div>
        <h1 style="margin:0;padding:0;">{icon} {title}</h1>
        {"<p style='color:#8B949E;margin:8px 0 0 0;font-size:0.95rem;letter-spacing:-0.01em;'>" + subtitle + "</p>" if subtitle else ""}
    </div>
    """, unsafe_allow_html=True)


def info_card(title: str, value: str, color: str = "#00D4FF", icon: str = ""):
    st.markdown(f"""
    <div style="
        background: rgba(22,27,34,0.7);
        backdrop-filter: blur(10px);
        border: 1px solid #21262D;
        border-left: 3px solid {color};
        border-radius: 12px;
        padding: 16px 20px;
        text-align: center;
        transition: all 0.2s;
    ">
        <div style="color:#6E7681;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.1em;font-weight:500;">{icon} {title}</div>
        <div style="color:{color};font-size:1.7rem;font-weight:700;margin-top:4px;letter-spacing:-0.03em;">{value}</div>
    </div>
    """, unsafe_allow_html=True)


def badge(text: str, color: str = "#00D4FF"):
    return (
        f'<span style="background:rgba(0,212,255,0.08);color:{color};'
        f'border:1px solid {color};border-radius:20px;'
        f'padding:2px 10px;font-size:0.73rem;font-weight:600;">{text}</span>'
    )


# Ordered page manifest — (file path relative to app root, label, icon)
PAGES = [
    ("app",                              "Home",                  ":material/home:"),
    ("pages/10_Preprocessing_Workbench", "Preprocessing Workbench", ":material/build:"),
    ("pages/1_Upload_Data",              "Upload Data",           ":material/upload_file:"),
    ("pages/2_Quality_Control",          "Quality Control",       ":material/biotech:"),
    ("pages/3_Clustering_UMAP",          "Clustering & UMAP",     ":material/monitoring:"),
    ("pages/4_Cell_Type_Annotation",     "Cell Type Annotation",  ":material/sell:"),
    ("pages/5_Gene_Explorer",            "Gene Explorer",         ":material/search:"),
    ("pages/6_Differential_Expression",  "Diff. Expression",      ":material/query_stats:"),
    ("pages/7_Pathway_Analysis",         "Pathway Analysis",      ":material/route:"),
    ("pages/8_Clinical_Report",          "Clinical Report",       ":material/description:"),
    ("pages/9_Team_Dashboard",           "Team Dashboard",        ":material/groups:"),
]


def render_nav_buttons(current_idx: int):
    """Render Prev / Next page navigation buttons at the bottom of any page.

    Parameters
    ----------
    current_idx : int
        Index of the current page in PAGES (0 = Home, 1 = Upload, ..., 8 = Report).
    """
    st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)
    st.divider()

    prev_idx = current_idx - 1 if current_idx > 0 else None
    next_idx = current_idx + 1 if current_idx < len(PAGES) - 1 else None

    col_prev, col_center, col_next = st.columns([1, 2, 1])

    if prev_idx is not None:
        prev_path, prev_label, prev_icon = PAGES[prev_idx]
        with col_prev:
            if st.button(f"← {prev_icon} {prev_label}", key="nav_prev", use_container_width=True):
                page_file = "app.py" if prev_path == "app" else f"{prev_path}.py"
                st.switch_page(page_file)

    with col_center:
        # Progress dots
        dots_html = '<div style="display:flex;justify-content:center;align-items:center;gap:6px;padding:8px 0;">'
        for i, (_, lbl, ico) in enumerate(PAGES):
            if i == current_idx:
                dots_html += f'<span title="{lbl}" style="width:28px;height:8px;background:#00D4FF;border-radius:4px;display:inline-block;"></span>'
            elif i < current_idx:
                dots_html += f'<span title="{lbl}" style="width:8px;height:8px;background:#51CF66;border-radius:50%;display:inline-block;opacity:0.7;"></span>'
            else:
                dots_html += f'<span title="{lbl}" style="width:8px;height:8px;background:#30363D;border-radius:50%;display:inline-block;"></span>'
        dots_html += "</div>"
        st.markdown(dots_html, unsafe_allow_html=True)
        _, lbl, ico = PAGES[current_idx]
        st.markdown(f'<p style="text-align:center;color:#6E7681;font-size:0.75rem;margin:0;">Step {current_idx} of {len(PAGES)-1} — {ico} {lbl}</p>', unsafe_allow_html=True)

    if next_idx is not None:
        next_path, next_label, next_icon = PAGES[next_idx]
        with col_next:
            if st.button(f"{next_icon} {next_label} →", key="nav_next", type="primary", use_container_width=True):
                page_file = "app.py" if next_path == "app" else f"{next_path}.py"
                st.switch_page(page_file)
