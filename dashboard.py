"""Cambridge Crime Analytics - Streamlit dashboard over the CPD daily-log pipeline.

Full-redesign build (Hallmark, scope: app). Data flows straight from the cpd_incidents
table through cached loading, a single filtered frame, and derived aggregations; every
figure on screen is computed from real records, never hard-coded.
"""
import html
import os
from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    try:
        DATABASE_URL = st.secrets["DATABASE_URL"]
    except Exception:
        DATABASE_URL = None
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///cpd_local.db"

st.set_page_config(page_title="Cambridge Crime Analytics", page_icon="🛡", layout="wide")

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_ABBR = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# ═════════════════════════════  THEME TOKENS  ═══════════════════════════════════
# Single source of truth: the same palette drives the CSS token block and Plotly.

PALETTES = {
    "dark": {
        "bg": "#0f1216", "surface": "#151a21", "raised": "#1b222b",
        "border": "#2a3341", "rule": "#212933",
        "ink": "#e8ebf0", "muted": "#98a2b0", "faint": "#7e8a9a",
        "accent": "#e5484d", "accent_strong": "#f2555a", "accent_dim": "#8c2a30",
        "accent_soft": "rgba(229,72,77,0.12)", "dim_soft": "rgba(229,72,77,0.28)",
        "ok": "#4cc38a", "ok_soft": "rgba(76,195,138,0.14)",
        "heat_lo": "#131013", "heat_hi": "#ff6b6f",
        "donut_line": "#0f1216", "plot_face": "#0f1216",
        "knob": "#dfe6ee", "knob_left": "4px",
        "icon_left": "auto", "icon_right": "9px",
        "ramp": ["#e5484d", "#c73a3f", "#a92e34", "#8a2429", "#6b1b20", "#501418", "#3a0f13", "#28090b"],
        "other": "#5d6a7d",
        "chart_grid": "#212933",
    },
    "light": {
        "bg": "#f6f7f9", "surface": "#ffffff", "raised": "#eef1f5",
        "border": "#dde3ea", "rule": "#e7ebf0",
        "ink": "#1c222b", "muted": "#565f6c", "faint": "#6e7987",
        "accent": "#c4343a", "accent_strong": "#d33c41", "accent_dim": "#d8848a",
        "accent_soft": "rgba(196,52,58,0.10)", "dim_soft": "rgba(196,52,58,0.22)",
        "ok": "#18855a", "ok_soft": "rgba(24,133,90,0.12)",
        "heat_lo": "#f6f7f9", "heat_hi": "#a5252b",
        "donut_line": "#ffffff", "plot_face": "#f6f7f9",
        "knob": "#343b46", "knob_left": "calc(100% - 30px)",
        "icon_left": "9px", "icon_right": "auto",
        "ramp": ["#c4343a", "#a12b30", "#822227", "#651a1f", "#4a1317", "#330d10", "#21080a", "#150507"],
        "other": "#9aa4b1",
        "chart_grid": "#e7ebf0",
    },
}

if "theme" not in st.session_state:
    st.session_state.theme = st.query_params.get("theme", "dark")
T = PALETTES[st.session_state.theme]
FONT_UI = "Inter, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif"
FONT_TOKEN = "var(--font-ui)"

# Theme-toggle pill icon (the mode you are in) and knob position, as tokens.
_MOON = ("url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
         "viewBox='0 0 24 24' fill='%23e8ebf0'%3E%3Cpath d='M12.3 2a10 10 0 0 0-.19 20 "
         "10 10 0 0 0 8.09-4.11 1 1 0 0 0-1-1.49 8 8 0 1 1-8.4-13.4 1 1 0 0 0 1.5-1z'/%3E"
         "%3Cpath d='M19 2.5l.5 1.2 1.2.5-1.2.5-.5 1.2-.5-1.2-1.2-.5 1.2-.5z'/%3E"
         "%3Cpath d='M20.5 8l.4.9.9.4-.9.4-.4.9-.4-.9-.9-.4.9-.4z'/%3E%3C/svg%3E\")")
_SUN = ("url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
        "viewBox='0 0 24 24' fill='none' stroke='%231c222b' stroke-width='2.2' "
        "stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='4'/%3E"
        "%3Cline x1='12' y1='1' x2='12' y2='3'/%3E%3Cline x1='12' y1='21' x2='12' y2='23'/%3E"
        "%3Cline x1='4.22' y1='4.22' x2='5.64' y2='5.64'/%3E%3Cline x1='18.36' y1='18.36' "
        "x2='19.78' y2='19.78'/%3E%3Cline x1='1' y1='12' x2='3' y2='12'/%3E"
        "%3Cline x1='21' y1='12' x2='23' y2='12'/%3E%3Cline x1='4.22' y1='19.78' "
        "x2='5.64' y2='18.36'/%3E%3Cline x1='18.36' y1='5.64' x2='19.78' y2='4.22'/%3E%3C/svg%3E\")")
TOGGLE_ICON = _MOON if st.session_state.theme == "dark" else _SUN

# ═════════════════════════════════  CSS  ════════════════════════════════════════
st.markdown(
    f"""
<style>
  /* Hallmark · 2026-11-09 · shape: app screen · genre: modern-minimal (inferred)
   * theme: by request (professional dark, single red signal accent, Inter)
   * redesign: full · scope: app
   * critique: the old screen hid behind a terminal pastiche - mono for everything,
   * tracked-caps labels, charts with bare axes, a feed that could not be searched,
   * sorted or paged, and a weekly-only trend. The rebuild keeps the density and the
   * incident-table spine but adds a real token system, labelled axes, honest deltas,
   * a day-by-hour signature heatmap and a working incident table.
   * waive 63: the live dot is the requested data-freshness indicator, always paired
   * with the record count and last ETL timestamp - state, not ornament
   * waive 38iii: the accented "Analytics" in the wordmark is the theme's signature,
   * named by request, and appears once on the screen */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

  :root {{
    --bg: {T["bg"]}; --surface: {T["surface"]}; --raised: {T["raised"]};
    --border: {T["border"]}; --rule: {T["rule"]};
    --ink: {T["ink"]}; --muted: {T["muted"]}; --faint: {T["faint"]};
    --accent: {T["accent"]}; --accent-strong: {T["accent_strong"]};
    --accent-dim: {T["accent_dim"]}; --accent-soft: {T["accent_soft"]};
    --dim-soft: {T["dim_soft"]}; --ok: {T["ok"]}; --ok-soft: {T["ok_soft"]};
    --font-ui: {FONT_UI};
    --knob: {T["knob"]}; --knob-left: {T["knob_left"]};
    --icon-left: {T["icon_left"]}; --icon-right: {T["icon_right"]};
    --icon-toggle: {TOGGLE_ICON};
  }}
  html, body {{ overflow-x: clip; }}
  .stApp {{ background: var(--bg); color: var(--ink); font-family: var(--font-ui); }}
  header[data-testid="stHeader"] {{ display: none; }}
  section[data-testid="stSidebar"] {{ display: none; }}
  .block-container {{ padding: 1rem 1.25rem 2.25rem 1.25rem !important; max-width: 100% !important; }}
  p, li, label {{ font-family: var(--font-ui); }}
  [data-testid="stPlotlyChart"] {{ margin: 0.15rem 0 0.85rem 0; }}
  ::selection {{ background: var(--dim-soft); color: var(--ink); }}

  button:focus-visible, input:focus-visible, [contenteditable]:focus-visible,
  [data-testid="stDateInputField"]:focus-visible,
  [data-testid="stTextInput"] input:focus-visible,
  [data-testid="stMultiSelect"] [role="group"]:focus-visible,
  [data-testid="stSelectbox"] input:focus-visible,
  [data-testid="stMultiSelect"] [data-tag]:focus-visible {{
    outline: 2px solid var(--accent); outline-offset: 2px;
  }}

  /* ── Native widget surfaces (Streamlit 1.65 react-aria DOM) ── */
  [data-testid="stWidgetLabel"] p {{
    font-family: var(--font-ui); font-size: 0.8rem; color: var(--muted);
    margin-bottom: 0.2rem; letter-spacing: 0; text-transform: none;
  }}
  [data-testid="stDateInputField"],
  [data-testid="stTextInputField"],
  [data-testid="stSelectbox"] input[type="text"],
  [data-testid="stMultiSelect"] [role="group"] {{
    background: var(--surface) !important; color: var(--ink) !important;
    border: 1px solid var(--border) !important; border-radius: 6px !important;
    font-family: var(--font-ui) !important; font-size: 0.88rem !important;
    min-height: 2.3rem;
  }}
  [data-testid="stDateInputField"] [contenteditable] {{ color: var(--ink) !important; }}
  [data-testid="stTextInput"] input {{ height: 2.3rem; font-size: 0.88rem; }}
  [data-testid="stTextInput"] input::placeholder {{ color: var(--faint); opacity: 1; }}
  [data-testid="stDateInputField"]:hover,
  [data-testid="stTextInput"] input:hover,
  [data-testid="stSelectbox"] input[type="text"]:hover {{
    border-color: var(--faint) !important;
  }}
  [data-testid="stSelectbox"] button {{
    color: var(--muted) !important; background: transparent !important;
  }}
  [data-testid="stMultiSelect"] [data-tag] {{
    background: var(--raised) !important; color: var(--ink) !important;
    border: 1px solid var(--border) !important;
    font-family: var(--font-ui) !important; font-size: 0.8rem !important;
  }}
  [data-testid="stDateInput"] svg, [data-testid="stTextInput"] svg,
  [data-testid="stSelectbox"] svg, [data-testid="stMultiSelect"] svg {{ color: var(--muted); }}
  /* Segmented control (react-aria radio group) */
  [data-testid="stButtonGroup"] button[data-variant="segmented_control"] {{
    background: var(--surface) !important; color: var(--muted) !important;
    border: 1px solid var(--border) !important; border-radius: 6px !important;
    font-family: var(--font-ui) !important; font-size: 0.82rem !important;
    transition: color 0.15s ease, border-color 0.15s ease;
  }}
  [data-testid="stButtonGroup"] button[data-variant="segmented_control"]:hover {{
    color: var(--ink) !important;
  }}
  [data-testid="stButtonGroup"] button[data-variant="segmented_control"]:active {{
    color: var(--ink) !important; background: var(--raised) !important;
  }}
  [data-testid="stButtonGroup"] button[data-variant="segmented_control"][data-selected="true"] {{
    background: var(--accent-soft) !important; color: var(--accent-strong) !important;
    border-color: var(--accent) !important;
  }}
  [data-testid="stButton"] > button {{
    background: transparent; color: var(--muted);
    border: 1px solid var(--border); border-radius: 6px;
    font-family: var(--font-ui); font-size: 0.84rem; height: 2.3rem; padding: 0 0.9rem;
    transition: color 0.15s ease, border-color 0.15s ease;
  }}
  [data-testid="stButton"] > button:hover {{ color: var(--ink); border-color: var(--faint); }}
  [data-testid="stButton"] > button:active {{ color: var(--ink); background: var(--raised); }}

  /* ── Theme toggle pill ── */
  .st-key-theme_toggle {{
    display: flex; justify-content: flex-end; align-items: center;
    height: 100%; margin: 0;
  }}
  .st-key-theme_toggle [data-testid="stButton"] {{ margin: 0; height: 100%; display: flex; align-items: center; }}
  .st-key-theme_toggle button {{
    width: 64px !important; height: 32px !important; min-height: 32px !important;
    max-height: 32px !important; border-radius: 9999px !important; position: relative !important;
    cursor: pointer !important; border: 1px solid var(--border) !important;
    background: var(--raised) !important; padding: 0 !important;
    box-shadow: none !important; overflow: hidden !important;
    transition: border-color 0.15s ease !important;
  }}
  .st-key-theme_toggle button:hover {{ border-color: var(--faint) !important; }}
  .st-key-theme_toggle button::before {{
    content: "" !important; position: absolute !important; top: 2px !important;
    left: var(--knob-left) !important; width: 26px !important; height: 26px !important;
    border-radius: 50% !important; background: var(--knob) !important; z-index: 2 !important;
  }}
  .st-key-theme_toggle button::after {{
    content: "" !important; position: absolute !important; top: 50% !important;
    left: var(--icon-left) !important; right: var(--icon-right) !important;
    transform: translateY(-50%) !important; width: 16px !important; height: 16px !important;
    background: var(--icon-toggle) center / contain no-repeat !important; z-index: 1 !important;
  }}
  .st-key-theme_toggle button p,
  .st-key-theme_toggle button div,
  .st-key-theme_toggle button span {{
    display: none !important; visibility: hidden !important;
  }}
  .st-key-theme_toggle button:focus,
  .st-key-theme_toggle button:focus-visible {{
    outline: 2px solid var(--accent) !important; outline-offset: 2px !important;
  }}

  /* ── Header ── */
  .topbar {{ display: flex; align-items: baseline; gap: 1rem; flex-wrap: wrap; padding: 0.15rem 0 0.5rem; }}
  .topbar h1 {{
    font-family: var(--font-ui); font-size: 1.3rem; font-weight: 700;
    color: var(--ink); letter-spacing: -0.01em; margin: 0;
  }}
  .topbar h1 .sig {{ color: var(--accent); }}
  .topbar h1 {{ text-wrap: balance; }}
  .status {{
    font-family: var(--font-ui); font-size: 0.8rem; color: var(--muted);
    display: inline-flex; align-items: center; gap: 0.45rem;
  }}
  .dot {{
    width: 7px; height: 7px; border-radius: 50%; background: var(--ok);
    animation: pulse 2.4s ease-in-out infinite;
  }}
  @keyframes pulse {{ 50% {{ opacity: 0.35; }} }}
  @media (prefers-reduced-motion: reduce) {{ .dot {{ animation: none; }} }}
  .masthead-rule {{ border-bottom: 1px solid var(--rule); margin: 0.2rem 0 1.1rem; }}

  /* ── Primary KPI cards ── */
  .kpi-row {{ display: flex; gap: 0.7rem; margin: 0.5rem 0 2.2rem; flex-wrap: wrap; }}
  .kpi {{
    flex: 1; min-width: 155px; min-height: 7.8rem; background: var(--surface);
    border: 1px solid var(--border); border-top: 2px solid var(--accent);
    border-radius: 6px; padding: 0.7rem 0.85rem 0.75rem;
    display: flex; flex-direction: column; justify-content: flex-start; box-sizing: border-box;
  }}
  .kpi .v {{
    font-family: var(--font-ui); font-size: 1.7rem; font-weight: 700;
    color: var(--ink); font-variant-numeric: tabular-nums; line-height: 1.15;
  }}
  .kpi .v.accent {{ color: var(--accent); }}
  .kpi .l {{
    font-family: var(--font-ui); font-size: 0.8rem; color: var(--muted); margin-top: 2px;
  }}
  .delta {{
    font-family: var(--font-ui); font-size: 0.76rem; font-variant-numeric: tabular-nums;
    display: block; margin-top: auto; white-space: nowrap; overflow: hidden;
    text-overflow: ellipsis;
  }}
  .delta.up {{ color: var(--accent); }}
  .delta.down {{ color: var(--ok); }}
  .delta.flat {{ color: var(--muted); }}

  /* ── Secondary stat strip ── */
  .strip {{
    display: flex; flex-wrap: wrap; background: var(--surface);
    border: 1px solid var(--border); border-radius: 6px;
    padding: 0.6rem 0.25rem; margin: 0 0 2.1rem;
  }}
  .strip .cell {{
    flex: 1 1 0; min-width: 122px; padding: 0.25rem 0.9rem;
    border-left: 1px solid var(--rule);
  }}
  .strip .cell:first-child {{ border-left: none; }}
  .strip .k {{
    font-family: var(--font-ui); font-size: 0.76rem; color: var(--muted); margin: 0;
  }}
  .strip .x {{
    font-family: var(--font-ui); font-size: 0.92rem; font-weight: 600; color: var(--ink);
    font-variant-numeric: tabular-nums; margin: 2px 0 0;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }}

  /* ── Panel labels (sentence case, body face, untracked) ── */
  .plabel {{
    font-family: var(--font-ui); font-size: 0.95rem; font-weight: 600;
    color: var(--ink); margin: 0.7rem 0 0.1rem;
  }}
  .psub {{ font-family: var(--font-ui); font-size: 0.8rem; color: var(--muted); margin: 0 0 0.3rem; }}

  /* ── Incident table ── */
  .feed-wrap {{ width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }}
  .feed {{ width: 100%; border-collapse: collapse; font-family: var(--font-ui); font-size: 0.85rem; min-width: 680px; }}
  .feed th {{
    text-align: left; color: var(--muted); font-weight: 600;
    border-bottom: 1px solid var(--border); padding: 8px 12px;
    font-size: 0.78rem; text-transform: none; letter-spacing: 0; white-space: nowrap;
  }}
  .feed td {{
    padding: 8px 12px; border-bottom: 1px solid var(--rule); color: var(--muted);
    vertical-align: top;
  }}
  .feed td.num, .feed th.num {{ font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .feed td.ink {{ color: var(--ink); font-weight: 500; }}
  .feed .desc {{ max-width: 420px; overflow-wrap: break-word; }}
  .feed tbody tr:nth-child(odd) td {{ background: color-mix(in srgb, var(--raised) 45%, transparent); }}
  .feed tbody tr:hover td {{ background: var(--accent-soft); color: var(--ink); }}
  .chip {{
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 0.74rem; font-weight: 600; border: 1px solid transparent; white-space: nowrap;
  }}
  .chip-arrest {{ background: var(--accent-soft); color: var(--accent-strong); border-color: var(--dim-soft); }}
  .chip-plain {{ background: var(--raised); color: var(--muted); border-color: var(--border); }}
  .pager {{ display: flex; align-items: center; gap: 0.6rem; margin: 0.55rem 0 0.3rem; }}
  .pager .info {{ font-family: var(--font-ui); font-size: 0.8rem; color: var(--muted); font-variant-numeric: tabular-nums; }}

  .empty {{
    background: var(--surface); border: 1px solid var(--border); border-radius: 6px;
    padding: 1.3rem; color: var(--muted); font-size: 0.92rem;
  }}

  /* ── Responsive ── */
  @media (max-width: 768px) {{
    .block-container {{ padding: 0.7rem 0.7rem 1.8rem 0.7rem !important; }}
    .topbar h1 {{ font-size: 1.05rem; }}
    .status {{ font-size: 0.72rem; }}
    .kpi {{ min-width: 125px; }}
    .kpi .v {{ font-size: 1.4rem; }}
    .kpi .l {{ font-size: 0.74rem; }}
    .strip .cell {{ min-width: 46%; border-left: none; }}
    .strip .x {{ font-size: 0.86rem; }}
    .plabel {{ font-size: 0.88rem; margin-top: 0.5rem; }}
    .feed {{ font-size: 0.78rem; min-width: 600px; }}
    .feed th, .feed td {{ padding: 4px 8px; }}
  }}
</style>
""",
    unsafe_allow_html=True,
)


# ════════════════════════════════  DATA  ════════════════════════════════════════

@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    df = pd.read_sql(
        "SELECT * FROM cpd_incidents",
        create_engine(DATABASE_URL),
        parse_dates=["date_time", "last_updated"],
    )
    # Invalid timestamps cannot sit on any axis: drop them once, here.
    df = df[df["date_time"].notna()].copy()
    return df


@st.cache_data(ttl=3600)
def catalogue(_df: pd.DataFrame) -> dict:
    types = sorted(_df["type"].dropna().astype(str).unique())
    return {"types": types, "rows": len(_df)}


df = load_data()
meta = catalogue(df)

# ═══════════════════════════════  HELPERS  ══════════════════════════════════════


def title_case(value) -> str:
    s = str(value).strip().title()
    return s if s and s.lower() != "nan" else "Unknown"


def base_layout(**kw) -> dict:
    lo = dict(
        paper_bgcolor=T["plot_face"], plot_bgcolor=T["plot_face"],
        font=dict(color=T["muted"], size=11, family=FONT_UI),
        margin=dict(l=4, r=8, t=10, b=44), showlegend=False,
        dragmode=False,  # static charts: no pan/zoom, hover only
    )
    lo.update(kw)
    return lo


def show(fig: go.Figure, h: int = 240, **kw) -> None:
    fig.update_layout(**{**base_layout(), **kw, "height": h})
    # theme=None keeps the figure's own layout (font colours/sizes); the default
    # "streamlit" theme re-colours ticks with the static config theme, which
    # washes labels out in the light theme.
    st.plotly_chart(fig, width="stretch", theme=None,
                    config={"displayModeBar": False, "scrollZoom": False})


def axes(fig: go.Figure, x_title: str = "", y_title: str = "", y_grid: bool = True) -> None:
    tick_space = dict(ticks="outside", ticklen=4, tickcolor=T["border"],
                      ticklabelstandoff=7,
                      tickfont=dict(size=10, color=T["muted"]),
                      fixedrange=True)
    fig.update_xaxes(
        title=dict(text=x_title, font=dict(size=11.5, color=T["faint"]), standoff=14),
        showgrid=False, linecolor=T["border"], color=T["muted"],
        automargin=True, **tick_space,
    )
    fig.update_yaxes(
        title=dict(text=y_title, font=dict(size=11.5, color=T["faint"]), standoff=14),
        showgrid=y_grid, gridcolor=T["chart_grid"], griddash=None,
        linecolor=T["border"], color=T["muted"],
        automargin=True, zeroline=False, **tick_space,
    )


def panel(label: str, sub: str = "") -> None:
    st.markdown(f'<div class="plabel">{label}</div>', unsafe_allow_html=True)
    if sub:
        st.markdown(f'<div class="psub">{sub}</div>', unsafe_allow_html=True)


def fmt_dt(ts) -> str:
    return pd.Timestamp(ts).strftime("%d %b %Y %H:%M")


def delta_chip(cur: int, prev: int, unit: str = "vs previous period") -> str:
    """Measured period-over-period change, never invented."""
    if prev <= 0:
        return f'<span class="delta flat">no prior-period records</span>'
    pct = (cur - prev) / prev * 100
    if pct >= 1:
        return f'<span class="delta up">▲ {pct:.0f}% {unit}</span>'
    if pct <= -1:
        return f'<span class="delta down">▼ {abs(pct):.0f}% {unit}</span>'
    return f'<span class="delta flat">= flat {unit}</span>'


# ═════════════════════════════  TOP BAR  ════════════════════════════════════════

top_left, top_right = st.columns([9, 1])
with top_left:
    last_etl = df["last_updated"].max()
    last_etl_s = fmt_dt(last_etl) if pd.notna(last_etl) else "n/a"
    st.markdown(
        f"""<div class="topbar">
          <h1>Cambridge Crime <span class="sig">Analytics</span></h1>
          <div class="status"><span class="dot"></span>Live&nbsp;&nbsp;|&nbsp;&nbsp;{len(df):,} records
          &nbsp;|&nbsp;&nbsp;last ETL update {last_etl_s}</div>
        </div>""",
        unsafe_allow_html=True,
    )
with top_right:
    if st.button("", key="theme_toggle", help="Switch theme"):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()

st.markdown('<div class="masthead-rule"></div>', unsafe_allow_html=True)

# ═════════════════════════════  FILTERS  ════════════════════════════════════════

mn, mx = df["date_time"].min().date(), df["date_time"].max().date()
if "f_range" not in st.session_state:
    st.session_state.f_range = (mn, mx)
if "f_types" not in st.session_state:
    st.session_state.f_types = meta["types"]
if "f_loc" not in st.session_state:
    st.session_state.f_loc = ""

fc1, fc2, fc3 = st.columns([2.2, 1.7, 1.7])
with fc1:
    date_range = st.date_input("Date range", min_value=mn, max_value=mx, key="f_range")
with fc2:
    sel_types = st.multiselect(
        "Record type", meta["types"], key="f_types",
        help="Record class as logged by CPD (incident, arrest, traffic, ...)",
    )
with fc3:
    loc_q = st.text_input("Location contains", key="f_loc", placeholder="e.g. Massachusetts Ave")

sel_types = sel_types or meta["types"]
if len(date_range) != 2:
    st.info("Pick a start and end date to view the analytics.")
    st.stop()
d_start, d_end = date_range

mask = df["date_time"].dt.date.between(d_start, d_end) & df["type"].isin(sel_types)
if loc_q.strip():
    needle = loc_q.strip().lower()
    mask &= df["location"].fillna("").str.lower().str.contains(needle, regex=False)
data = df[mask]

n_days = (d_end - d_start).days + 1

# ════════════════════════════  KPI COMPUTATION  ═════════════════════════════════

cur_n = len(data)
prev_start = d_start - timedelta(days=n_days)
prev_end = d_start - timedelta(days=1)
prev_mask = df["date_time"].dt.date.between(prev_start, prev_end) & df["type"].isin(sel_types)
if loc_q.strip():
    prev_mask &= df["location"].fillna("").str.lower().str.contains(needle, regex=False)
prev_n = int(prev_mask.sum())

arrests = int((data["type"] == "ARREST").sum())
latest_ts = data["date_time"].max()
if pd.isna(latest_ts):
    latest_ts = data["date_time"].min()

if data.empty:
    st.markdown(
        """<div class="empty">No incidents match the current filters. Widen the date range,
        clear the location search, or re-select record types.</div>""",
        unsafe_allow_html=True,
    )
    st.stop()

latest_day = data["date_time"].dt.date.max()
last7 = int((data["date_time"].dt.date > latest_day - timedelta(days=7)).sum())
last30 = int((data["date_time"].dt.date > latest_day - timedelta(days=30)).sum())
same_day = int((data["date_time"].dt.date == latest_day).sum())

top_subtype = data["subtype"].dropna()
top_subtype = top_subtype.mode().iat[0] if not top_subtype.empty else "n/a"
top_loc = data["location"].dropna()
top_loc = top_loc.mode().iat[0] if not top_loc.empty else "n/a"
peak_hour = int(data["hour"].mode().iat[0])
n_categories = int(data["subtype"].dropna().nunique())
n_locations = int(data["location"].dropna().nunique())

# ── KPI row 1: primary figures (single flex row; .kpi-row carries the spacing) ──
st.markdown(
    f"""<div class="kpi-row">
      <div class="kpi"><div class="v accent">{cur_n:,}</div>
        <div class="l">Total recorded incidents</div>
        {delta_chip(cur_n, prev_n)}</div>
      <div class="kpi"><div class="v">{arrests:,}</div>
        <div class="l">Arrests ({arrests / cur_n * 100:.1f}% of records)</div>
        <div class="delta flat">records of type “Arrest”</div></div>
      <div class="kpi"><div class="v">{cur_n / n_days:,.1f}</div>
        <div class="l">Average incidents per day</div>
        <div class="delta flat">over {n_days} days</div></div>
      <div class="kpi"><div class="v">{peak_hour:02d}:00</div>
        <div class="l">Peak crime hour</div>
        <div class="delta flat">most frequent reporting hour</div></div>
    </div>""",
    unsafe_allow_html=True,
)

# ── Secondary strip ──────────────────────────────────────────────────────────────
st.markdown(
    f"""<div class="strip">
      <div class="cell"><p class="k">On the latest day ({latest_day.strftime('%d %b')})</p>
        <p class="x">{same_day:,}</p></div>
      <div class="cell"><p class="k">Latest 7 days</p><p class="x">{last7:,}</p></div>
      <div class="cell"><p class="k">Latest 30 days</p><p class="x">{last30:,}</p></div>
      <div class="cell"><p class="k">Most reported offence</p><p class="x">{title_case(top_subtype)}</p></div>
      <div class="cell"><p class="k">Most affected location</p><p class="x">{title_case(top_loc)}</p></div>
      <div class="cell"><p class="k">Offence categories</p><p class="x">{n_categories:,}</p></div>
      <div class="cell"><p class="k">Unique locations</p><p class="x">{n_locations:,}</p></div>
    </div>""",
    unsafe_allow_html=True,
)

# ═════════════════════════════  ROW 1  ══════════════════════════════════════════
# Crime trend (interval switch + moving average) | offence-category donut

trend_col, donut_col = st.columns([2.1, 1])

with trend_col:
    panel("Crime trend over time", "Incident counts with a moving-average trend line")
    interval = st.segmented_control("Interval", ["Daily", "Weekly", "Monthly"], key="interval",
                                    default="Daily", label_visibility="collapsed")
    interval = interval or "Daily"

    series = data.set_index("date_time").sort_index().resample(
        {"Daily": "D", "Weekly": "W", "Monthly": "ME"}[interval]).size()
    if interval == "Daily":
        win, ma_label = 7, "7-day moving average"
    elif interval == "Weekly":
        win, ma_label = 4, "4-week moving average"
    else:
        win, ma_label = 3, "3-month moving average"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=series.index, y=series.values, name="Incidents",
        mode="lines", line=dict(color=T["accent"], width=2),
        fill="tozeroy", fillcolor=T["accent_soft"],
        hovertemplate="%{x|%d %b %Y}: %{y:,} incidents<extra></extra>",
    ))
    if len(series) > win:
        fig.add_trace(go.Scatter(
            x=series.index, y=series.rolling(win).mean(), name=ma_label,
            mode="lines", line=dict(color=T["muted"], width=1.4),
            hovertemplate="%{x|%d %b %Y}: %{y:,.1f} (avg)<extra></extra>",
        ))
    x_lab = "Date" if interval != "Monthly" else "Month"
    axes(fig, x_title=x_lab, y_title="Number of incidents")
    if fig.data and len(fig.data) > 1:
        fig.update_layout(
            showlegend=True,
            legend=dict(orientation="h", y=1.12, bgcolor=T["plot_face"],
                        font=dict(size=10, color=T["muted"])),
        )
    show(fig, h=290)

with donut_col:
    panel("Offence category distribution", "Top categories by share of records")
    sub_counts = data["subtype"].dropna().astype(str).value_counts()
    top_n = sub_counts.head(8)
    if len(sub_counts) > 8:
        top_n = pd.concat([top_n, pd.Series({"Other offences": sub_counts.iloc[8:].sum()})])
    labels = [title_case(s) for s in top_n.index]
    total_sub = int(top_n.sum())
    has_other = "Other offences" in top_n.index
    colors = [T["ramp"][i % len(T["ramp"])] for i in range(len(top_n))]
    if has_other:
        colors[-1] = T["other"]
    # Percent labels on slices; suppressed below 3% where they would overlap
    pcts = top_n.values / total_sub * 100
    text = [f"{p:.1f}%" if p >= 3 else "" for p in pcts]

    fig = go.Figure(go.Pie(
        labels=labels, values=top_n.values, hole=0.62, sort=False,
        marker=dict(colors=colors, line=dict(color=T["donut_line"], width=1.5)),
        text=text, textinfo="text", textposition="inside", insidetextorientation="horizontal",
        textfont=dict(size=10, color="#ffffff"),
        hovertemplate="%{label}<br>%{value:,} records (%{percent})<extra></extra>",
    ))
    fig.add_annotation(
        text=f"<b>{total_sub:,}</b><br><span style='font-size:10px'>categorised</span>",
        showarrow=False, font=dict(size=14, color=T["ink"]),
    )
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", y=-0.08, bgcolor=T["plot_face"],
                    font=dict(size=9.5, color=T["muted"])),
        margin=dict(l=4, r=4, t=10, b=10),
    )
    show(fig, h=290)

# ═════════════════════════════  ROW 2  ══════════════════════════════════════════
# Signature: day × hour heatmap, full width with a colour legend

panel("When the city reports", "Incident count by day of week and hour of day")
heat = pd.crosstab(data["day_of_week"], data["hour"]).reindex(
    index=DAY_ORDER, columns=range(24), fill_value=0)
fig = go.Figure(go.Heatmap(
    z=heat.values, x=list(range(24)), y=DAY_ABBR,
    colorscale=[[0, T["heat_lo"]], [0.35, T["accent_dim"]], [0.75, T["accent"]], [1, T["heat_hi"]]],
    showscale=True, xgap=2, ygap=2,
    colorbar=dict(
        title=dict(text="Incidents", side="right", font=dict(size=10, color=T["muted"])),
        thickness=10, len=0.85, tickfont=dict(size=9, color=T["muted"]),
        ticklen=3,
    ),
    hovertemplate="%{y}, %{x}:00 – %{z:,} incidents<extra></extra>",
))
fig.update_xaxes(
    title=dict(text="Hour of day", font=dict(size=11.5, color=T["faint"]), standoff=14),
    tickvals=list(range(0, 24, 2)),
    ticktext=[f"{h:02d}" for h in range(0, 24, 2)],
    showgrid=False, linecolor=T["border"], color=T["muted"], automargin=True,
    fixedrange=True,
    ticks="outside", ticklen=4, tickcolor=T["border"], ticklabelstandoff=7,
    tickfont=dict(size=10, color=T["muted"]),
)
fig.update_yaxes(title=dict(text="Day of week", font=dict(size=11.5, color=T["faint"]), standoff=14),
                 color=T["muted"], ticklabelstandoff=7, automargin=True, fixedrange=True,
                 tickfont=dict(size=10, color=T["muted"]),
                 autorange="reversed")
show(fig, h=280, margin=dict(l=4, r=60, t=10, b=44))

# ═════════════════════════════  ROW 3  ══════════════════════════════════════════
# Hour-of-day and day-of-week distributions

h_col, d_col = st.columns(2)

with h_col:
    panel("Incidents by hour of day", "All 24 hours; the peak hour is highlighted")
    hr = data.groupby("hour").size().reindex(range(24), fill_value=0)
    fig = go.Figure(go.Bar(
        x=list(range(24)), y=hr.values,
        marker=dict(color=[T["accent"] if v == hr.max() and v > 0 else T["accent_dim"]
                          for v in hr.values]),
        hovertemplate="%{x}:00 – %{y:,} incidents<extra></extra>",
    ))
    axes(fig, x_title="Hour of day", y_title="Number of incidents")
    fig.update_xaxes(tickvals=list(range(0, 24, 2)),
                     ticktext=[f"{h:02d}" for h in range(0, 24, 2)])
    show(fig, h=260)

with d_col:
    panel("Incidents by day of week", "Monday through Sunday; the busiest day is highlighted")
    dw = data["day_of_week"].value_counts().reindex(DAY_ORDER, fill_value=0)
    fig = go.Figure(go.Bar(
        x=DAY_ABBR, y=dw.values,
        marker=dict(color=[T["accent"] if v == dw.max() and v > 0 else T["accent_dim"]
                          for v in dw.values]),
        hovertemplate="%{x}: %{y:,} incidents<extra></extra>",
    ))
    axes(fig, x_title="Day of week", y_title="Number of incidents")
    show(fig, h=260)

# ═════════════════════════════  ROW 4  ══════════════════════════════════════════
# Ranked locations and offence descriptions

loc_col, off_col = st.columns(2)

with loc_col:
    top_locs = data["location"].dropna().astype(str).value_counts().head(10).iloc[::-1]
    panel("Top 10 most affected locations", "Street or block with the most records")
    y_labels = [title_case(v) if len(v) <= 30 else title_case(v)[:29] + "…" for v in top_locs.index]
    fig = go.Figure(go.Bar(
        x=top_locs.values, y=y_labels, orientation="h",
        marker=dict(color=T["accent_dim"]),
        hovertext=[title_case(v) for v in top_locs.index],
        hovertemplate="%{hovertext}: %{x:,} incidents<extra></extra>",
    ))
    axes(fig, x_title="Number of incidents", y_title="")
    fig.update_yaxes(tickfont=dict(size=9.5, color=T["muted"]))
    show(fig, h=290)

with off_col:
    top_offs = data["subtype"].dropna().astype(str).value_counts().head(10).iloc[::-1]
    panel("Top 10 recurring offences", "Most frequent offence descriptions on record")
    y_labels = [title_case(v) if len(v) <= 30 else title_case(v)[:29] + "…" for v in top_offs.index]
    fig = go.Figure(go.Bar(
        x=top_offs.values, y=y_labels, orientation="h",
        marker=dict(color=T["accent_dim"]),
        hovertext=[title_case(v) for v in top_offs.index],
        hovertemplate="%{hovertext}: %{x:,} incidents<extra></extra>",
    ))
    axes(fig, x_title="Number of incidents", y_title="")
    fig.update_yaxes(tickfont=dict(size=9.5, color=T["muted"]))
    show(fig, h=290)

# ═════════════════════════════  ROW 5  ══════════════════════════════════════════
# Weekday vs weekend rhythm, and month-by-month comparison across years

wk_col, mo_col = st.columns(2)

with wk_col:
    panel("Weekday vs weekend rhythm", "Average incidents per hour of day")
    dow_num = data["date_time"].dt.dayofweek
    weekend = data[dow_num >= 5]
    weekday = data[dow_num < 5]
    all_days = pd.date_range(d_start, d_end).dayofweek
    n_wknd = int((all_days >= 5).sum())
    n_wkdy = len(all_days) - n_wknd
    wknd_avg = (weekend.groupby("hour").size().reindex(range(24), fill_value=0) / max(n_wknd, 1))
    wkdy_avg = (weekday.groupby("hour").size().reindex(range(24), fill_value=0) / max(n_wkdy, 1))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(24)), y=wkdy_avg.values, name="Weekday average",
        mode="lines", line=dict(color=T["muted"], width=2),
        hovertemplate="Hour %{x}:00 – %{y:,.1f} incidents on average<extra>Weekday</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=list(range(24)), y=wknd_avg.values, name="Weekend average",
        mode="lines", line=dict(color=T["accent"], width=2),
        hovertemplate="Hour %{x}:00 – %{y:,.1f} incidents on average<extra>Weekend</extra>",
    ))
    axes(fig, x_title="Hour of day", y_title="Average incidents per hour")
    fig.update_xaxes(tickvals=list(range(0, 24, 3)),
                     ticktext=[f"{h:02d}" for h in range(0, 24, 3)])
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", y=1.12, bgcolor=T["plot_face"],
                    font=dict(size=9, color=T["muted"])),
    )
    show(fig, h=280)

with mo_col:
    panel("Monthly comparison across years", "Incidents per calendar month, one series per year")
    piv = data.assign(m=data["date_time"].dt.month).pivot_table(
        index="m", columns="year", values="id", aggfunc="count").fillna(0).reindex(
        range(1, 13), fill_value=0)
    years = sorted(piv.columns)
    fig = go.Figure()
    for i, yr in enumerate(years):
        is_latest = yr == years[-1]
        fig.add_trace(go.Bar(
            x=MONTH_ABBR, y=piv[yr].values, name=str(int(yr)),
            marker=dict(color=T["accent"] if is_latest else T["muted"]),
            hovertemplate="%{x} " + str(int(yr)) + ": %{y:,} incidents<extra></extra>",
        ))
    axes(fig, x_title="Month", y_title="Number of incidents")
    if len(years) > 1:
        fig.update_layout(
            barmode="group", showlegend=True,
            legend=dict(orientation="h", y=1.12, bgcolor=T["plot_face"],
                        font=dict(size=10, color=T["muted"])),
        )
    show(fig, h=280)

# ═══════════════════════════  INCIDENT TABLE  ═══════════════════════════════════

panel("Incident log", "The records behind every figure above - search, sort and page through them")

tc1, tc2 = st.columns([3, 1.2])
with tc1:
    q = st.text_input("Search the log", key="log_q", placeholder="Search offence, location or detail…")
with tc2:
    sort_choice = st.selectbox(
        "Sort by",
        ["Newest first", "Oldest first", "Type (A-Z)", "Location (A-Z)"], key="log_sort",
    )

table = data.copy()
if q.strip():
    needle2 = q.strip().lower()
    table = table[
        table[["type", "subtype", "location", "description"]]
        .fillna("")
        .apply(lambda row: needle2 in " ".join(map(str, row)).lower(), axis=1)
    ]

sort_map = {
    "Newest first": [("date_time", "desc")],
    "Oldest first": [("date_time", "asc")],
    "Type (A-Z)": [("type", "asc"), ("date_time", "desc")],
    "Location (A-Z)": [("location", "asc"), ("date_time", "desc")],
}
for col, direction in sort_map[sort_choice]:
    table = table.sort_values(col, ascending=direction == "asc", na_position="last")

PAGE = 15
total_rows = len(table)
max_page = max((total_rows - 1) // PAGE, 0)
if "log_page" not in st.session_state:
    st.session_state.log_page = 0
st.session_state.log_page = min(st.session_state.log_page, max_page)

pc1, pc2, pc3 = st.columns([1, 6, 1])
with pc1:
    if st.button("← Prev", disabled=st.session_state.log_page == 0):
        st.session_state.log_page -= 1
        st.rerun()
with pc3:
    if st.button("Next →", disabled=st.session_state.log_page >= max_page):
        st.session_state.log_page += 1
        st.rerun()
with pc2:
    st.markdown(
        f"""<div class="pager"><span class="info">
        Page {st.session_state.log_page + 1:,} of {max_page + 1:,}
        &nbsp;|&nbsp;&nbsp;{total_rows:,} matching records</span></div>""",
        unsafe_allow_html=True,
    )

page_df = table.iloc[st.session_state.log_page * PAGE:(st.session_state.log_page + 1) * PAGE]
rows = []
for _, r in page_df.iterrows():
    is_arrest = r["type"] == "ARREST"
    chip_cls = "chip-arrest" if is_arrest else "chip-plain"
    chip = f'<span class="chip {chip_cls}">{html.escape(str(r["type"]))}</span>'
    dt = r["date_time"].strftime("%d %b %Y %H:%M")
    sub = title_case(r["subtype"]) if pd.notna(r["subtype"]) else "—"
    loc = title_case(r["location"]) if pd.notna(r["location"]) else "—"
    desc = str(r["description"]) if pd.notna(r["description"]) else "—"
    short = desc if len(desc) <= 120 else desc[:118] + "…"
    rows.append(
        f"<tr><td class='num'>{dt}</td><td>{chip}</td><td class='ink'>{html.escape(sub)}</td>"
        f"<td>{html.escape(loc)}</td><td class='desc' title='{html.escape(desc, quote=True)}'>"
        f"{html.escape(short)}</td></tr>"
    )

st.markdown(
    f"""<div class="feed-wrap"><table class="feed">
    <thead><tr><th class="num">Date and time</th><th>Type</th><th>Offence</th>
    <th>Location</th><th>Details</th></tr></thead>
    <tbody>{''.join(rows) if rows else
        "<tr><td colspan='5'>Nothing matches this search on the current filters.</td></tr>"}
    </tbody></table></div>""",
    unsafe_allow_html=True,
)
