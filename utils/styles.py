"""Shared CSS/styling injected into every page."""
import streamlit as st

PLOTLY_TEMPLATE = "plotly_dark"

PALETTE = [
    "#00D4FF", "#7B2FBE", "#FF6B6B", "#51CF66", "#FFD43B",
    "#FF922B", "#74C0FC", "#F783AC", "#A9E34B", "#63E6BE",
    "#E599F7", "#FFA94D", "#4DABF7", "#FF8787", "#66D9E8",
]

def inject_global_css():
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
        color: #6E7681 !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        letter-spacing: -0.01em !important;
        transition: all 0.15s ease !important;
        border: 1px solid transparent !important;
        display: block !important;
    }
    [data-testid="stSidebarNavItems"] a:hover {
        background: rgba(0,212,255,0.06) !important;
        color: #C9D1D9 !important;
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
        color: #8B949E !important;
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
        color: #6E7681 !important;
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
        color: #000000 !important;
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
        color: #6E7681 !important;
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
    completed = st.session_state.get("pipeline_status", {})
    pipeline_steps = [
        ("Upload",           "📂"),
        ("QC",               "🔬"),
        ("Clustering",       "📊"),
        ("Annotation",       "🏷️"),
        ("Gene Explorer",    "🔍"),
        ("Diff. Expression", "📈"),
        ("Pathway",          "🧪"),
        ("Report",           "📄"),
    ]

    progress_items = ""
    for step, icon in pipeline_steps:
        done = completed.get(step) == "done"
        if done:
            color = "#51CF66"
            dot   = "✓"
            t_style = f"color:{color};font-weight:600;"
        else:
            color = "#30363D"
            dot   = "○"
            t_style = "color:#6E7681;"
        progress_items += (
            f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0;">'
            f'<span style="color:{color};font-size:0.75rem;width:14px;text-align:center;">{dot}</span>'
            f'<span style="{t_style}font-size:0.78rem;">{icon} {step}</span>'
            f'</div>'
        )

    sidebar_html = (
        '<div style="padding:16px 14px 0;">'
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">'
        '<div style="background:linear-gradient(135deg,rgba(0,212,255,0.15),rgba(123,47,190,0.15));'
        'border:1px solid rgba(0,212,255,0.25);border-radius:10px;width:36px;height:36px;'
        'display:flex;align-items:center;justify-content:center;font-size:1.1rem;flex-shrink:0;">🧬</div>'
        '<div>'
        '<div style="color:#E6EDF3;font-weight:700;font-size:0.88rem;letter-spacing:-0.02em;line-height:1.2;">SingleCell Explorer</div>'
        '<div style="color:#6E7681;font-size:0.7rem;">Clinical &amp; Research Platform</div>'
        '</div></div>'
        '<div style="display:flex;gap:5px;margin-bottom:14px;">'
        '<span style="background:rgba(81,207,102,0.1);color:#51CF66;border:1px solid rgba(81,207,102,0.3);border-radius:20px;padding:2px 8px;font-size:0.67rem;font-weight:600;">● LIVE</span>'
        '<span style="background:rgba(0,212,255,0.06);color:#6E7681;border:1px solid #21262D;border-radius:20px;padding:2px 8px;font-size:0.67rem;">v1.0.0</span>'
        '</div>'
        '<div style="border-top:1px solid #21262D;padding-top:12px;margin-bottom:4px;">'
        '<div style="color:#6E7681;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.1em;font-weight:600;margin-bottom:6px;">Pipeline Progress</div>'
        + progress_items +
        '</div></div>'
        '<div style="border-top:1px solid #161B22;margin-top:8px;padding-top:6px;"></div>'
    )
    st.sidebar.markdown(sidebar_html, unsafe_allow_html=True)


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
    ("app",                              "Home",                  "🏠"),
    ("pages/1_Upload_Data",              "Upload Data",           "📂"),
    ("pages/2_Quality_Control",          "Quality Control",       "🔬"),
    ("pages/3_Clustering_UMAP",          "Clustering & UMAP",     "📊"),
    ("pages/4_Cell_Type_Annotation",     "Cell Type Annotation",  "🏷️"),
    ("pages/5_Gene_Explorer",            "Gene Explorer",         "🔍"),
    ("pages/6_Differential_Expression",  "Diff. Expression",      "📈"),
    ("pages/7_Pathway_Analysis",         "Pathway Analysis",      "🧪"),
    ("pages/8_Clinical_Report",          "Clinical Report",       "📄"),
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
                st.switch_page(f"{prev_path}.py")

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
                st.switch_page(f"{next_path}.py")

