"""Streamlit dashboard – Cambridge PD daily log. Responsive + light/dark theme."""
import os

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

DAY_ORDER_FULL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_ABBR = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

st.set_page_config(page_title="CPD Dashboard", page_icon="🔴", layout="wide")

# ═══════════════════════════  THEME  ═════════════════════════════════════════

if "theme" not in st.session_state:
    st.session_state.theme = "dark"

DARK = {
    "bg": "#0a0a0a", "card": "#111111", "border": "#1e1e1e",
    "red": "#dc2626", "red_dim": "#7f1d1d", "red_glow": "#ef4444",
    "txt": "#d4d4d4", "dim": "#666666",
    "chart_grid": "#1e1e1e", "chart_fill": "rgba(220,38,38,0.08)",
    "donut_line": "#0a0a0a", "heat_base": "#0a0a0a",
}
LIGHT = {
    "bg": "#f5f5f5", "card": "#ffffff", "border": "#e0e0e0",
    "red": "#dc2626", "red_dim": "#fecaca", "red_glow": "#ef4444",
    "txt": "#1a1a1a", "dim": "#888888",
    "chart_grid": "#e5e5e5", "chart_fill": "rgba(220,38,38,0.10)",
    "donut_line": "#ffffff", "heat_base": "#f5f5f5",
}

T = DARK if st.session_state.theme == "dark" else LIGHT
is_dark = st.session_state.theme == "dark"

# ═══════════════════════════  CSS  ═══════════════════════════════════════════

toggle_css = """
  /* ── Pill Theme Toggle (Dark Mode) ── */
  .st-key-theme_toggle {
    display: flex;
    justify-content: flex-end;
    align-items: center;
  }
  .st-key-theme_toggle button {
    width: 70px !important;
    height: 34px !important;
    min-height: 34px !important;
    max-height: 34px !important;
    border-radius: 9999px !important;
    position: relative !important;
    cursor: pointer !important;
    border: 1px solid #333336 !important;
    background: #1c1c1f !important;
    padding: 0 !important;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.6) !important;
    transition: all 0.25s ease !important;
    overflow: hidden !important;
  }
  .st-key-theme_toggle button:hover {
    border-color: #4b4b52 !important;
    filter: brightness(1.1) !important;
  }
  /* Knob on left (white moon/sun orb) */
  .st-key-theme_toggle button::before {
    content: "" !important;
    position: absolute !important;
    top: 3px !important;
    left: 4px !important;
    width: 26px !important;
    height: 26px !important;
    border-radius: 50% !important;
    background: radial-gradient(circle at 35% 35%, #ffffff 0%, #e2e8f0 70%, #cbd5e1 100%) !important;
    box-shadow: 0 2px 5px rgba(0,0,0,0.5) !important;
    z-index: 2 !important;
  }
  /* Moon + stars icon on right */
  .st-key-theme_toggle button::after {
    content: "" !important;
    position: absolute !important;
    top: 50% !important;
    right: 10px !important;
    transform: translateY(-50%) !important;
    width: 17px !important;
    height: 17px !important;
    background-repeat: no-repeat !important;
    background-position: center !important;
    background-size: contain !important;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23ffffff'%3E%3Cpath d='M12.3 2a10 10 0 0 0-.19 20 10 10 0 0 0 8.09-4.11 1 1 0 0 0-1-1.49 8 8 0 1 1-8.4-13.4 1 1 0 0 0 1.5-1z'/%3E%3Cpath d='M19 2.5l.5 1.2 1.2.5-1.2.5-.5 1.2-.5-1.2-1.2-.5 1.2-.5z'/%3E%3Cpath d='M20.5 8l.4.9.9.4-.9.4-.4.9-.4-.9-.9-.4.9-.4z'/%3E%3C/svg%3E") !important;
    z-index: 1 !important;
  }
""" if is_dark else """
  /* ── Pill Theme Toggle (Light Mode) ── */
  .st-key-theme_toggle {
    display: flex;
    justify-content: flex-end;
    align-items: center;
  }
  .st-key-theme_toggle button {
    width: 70px !important;
    height: 34px !important;
    min-height: 34px !important;
    max-height: 34px !important;
    border-radius: 9999px !important;
    position: relative !important;
    cursor: pointer !important;
    border: 1px solid #d4d4d8 !important;
    background: #e4e4e7 !important;
    padding: 0 !important;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.08) !important;
    transition: all 0.25s ease !important;
    overflow: hidden !important;
  }
  .st-key-theme_toggle button:hover {
    border-color: #a1a1aa !important;
    filter: brightness(0.98) !important;
  }
  /* Knob on right (dark charcoal orb) */
  .st-key-theme_toggle button::before {
    content: "" !important;
    position: absolute !important;
    top: 3px !important;
    right: 4px !important;
    width: 26px !important;
    height: 26px !important;
    border-radius: 50% !important;
    background: radial-gradient(circle at 35% 35%, #3f3f46 0%, #27272a 70%, #18181b 100%) !important;
    box-shadow: 0 2px 5px rgba(0,0,0,0.25) !important;
    z-index: 2 !important;
  }
  /* Sun icon on left */
  .st-key-theme_toggle button::after {
    content: "" !important;
    position: absolute !important;
    top: 50% !important;
    left: 10px !important;
    transform: translateY(-50%) !important;
    width: 18px !important;
    height: 18px !important;
    background-repeat: no-repeat !important;
    background-position: center !important;
    background-size: contain !important;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2318181b' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='4'/%3E%3Cline x1='12' y1='1' x2='12' y2='3'/%3E%3Cline x1='12' y1='21' x2='12' y2='23'/%3E%3Cline x1='4.22' y1='4.22' x2='5.64' y2='5.64'/%3E%3Cline x1='18.36' y1='18.36' x2='19.78' y2='19.78'/%3E%3Cline x1='1' y1='12' x2='3' y2='12'/%3Cline x1='21' y1='12' x2='23' y2='12'/%3Cline x1='4.22' y1='19.78' x2='5.64' y2='18.36'/%3Cline x1='18.36' y1='5.64' x2='19.78' y2='4.22'/%3E%3C/svg%3E") !important;
    z-index: 1 !important;
  }
"""

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

  .stApp {{ background:{T["bg"]}; color:{T["txt"]}; }}
  header[data-testid="stHeader"] {{ display:none }}
  .block-container {{ padding:0.5rem 1rem 0.5rem 1rem !important; max-width:100%!important }}
  section[data-testid="stSidebar"] {{ display:none }}
  [data-testid="stPlotlyChart"] {{ margin:-0.2rem 0 -0.4rem 0 }}

  /* ── Header bar ── */
  .hdr {{
    display:flex; justify-content:flex-start; align-items:baseline;
    gap: 0.8rem; flex-wrap: wrap; padding: 0.15rem 0;
  }}
  .hdr h1 {{
    font-family:'JetBrains Mono',monospace; font-size:1.05rem; font-weight:700;
    color:{T["red"]}; letter-spacing:2px; margin:0;
  }}
  .hdr .info {{
    font-family:'JetBrains Mono',monospace; font-size:0.62rem; color:{T["dim"]};
  }}
  .hdr-line {{
    border-bottom:1px solid {T["red_dim"]};
    margin: 0.1rem 0 0.5rem 0;
  }}
  .dot {{
    display:inline-block; width:6px; height:6px; background:{T["red"]};
    border-radius:50%; box-shadow:0 0 6px {T["red"]}; margin-right:4px;
    animation:pulse 2s infinite;
  }}
  @keyframes pulse {{ 50%{{opacity:.3}} }}

  /* Hide inner Streamlit button labels for the toggle */
  .st-key-theme_toggle button p,
  .st-key-theme_toggle button div,
  .st-key-theme_toggle button span {{
    display: none !important;
    visibility: hidden !important;
  }}
  .st-key-theme_toggle button:focus,
  .st-key-theme_toggle button:focus-visible {{
    outline: none !important;
    box-shadow: none !important;
  }}

  {toggle_css}

  /* ── Stat cards ── */
  .stats {{
    display:flex; gap:0.5rem; margin-bottom:0.5rem;
    flex-wrap: wrap;
  }}
  .st-card {{
    flex:1; min-width: 100px;
    background:{T["card"]}; border:1px solid {T["border"]}; border-top:2px solid {T["red"]};
    border-radius:4px; padding:0.4rem 0.6rem; text-align:center;
  }}
  .st-card .v {{
    font-family:'JetBrains Mono',monospace; font-size:1.3rem; font-weight:700; color:{T["txt"]};
  }}
  .st-card .v.red {{ color:{T["red"]} }}
  .st-card .l {{
    font-family:'JetBrains Mono',monospace; font-size:0.55rem; color:{T["dim"]};
    text-transform:uppercase; letter-spacing:1.5px; margin-top:2px;
  }}

  /* ── Panel label ── */
  .plbl {{
    font-family:'JetBrains Mono',monospace; font-size:0.6rem; color:{T["red"]};
    text-transform:uppercase; letter-spacing:2px; margin-bottom:0.15rem;
  }}

  /* ── Feed table ── */
  .feed-wrap {{
    width:100%; overflow-x:auto; -webkit-overflow-scrolling:touch;
  }}
  .feed {{
    width:100%; border-collapse:collapse;
    font-family:'JetBrains Mono',monospace; font-size:0.65rem;
    min-width: 600px;
  }}
  .feed th {{
    text-align:left; color:{T["red"]}; font-weight:400;
    border-bottom:1px solid {T["red_dim"]};
    padding:4px 8px; text-transform:uppercase; letter-spacing:1px; font-size:0.55rem;
    position: sticky; top: 0; background: {T["card"]};
  }}
  .feed td {{
    padding:4px 8px; border-bottom:1px solid {T["border"]}; color:{T["dim"]};
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:220px;
  }}
  .feed tr:hover td {{ color:{T["txt"]}; background:{T["red_dim"]}18 }}
  .badge {{
    display:inline-block; padding:1px 6px; border-radius:3px;
    font-size:0.55rem; font-weight:600;
  }}
  .badge-a {{ background:{T["red_dim"]}; color:{T["red_glow"]} }}
  .badge-o {{ background:{T["border"]}; color:{T["dim"]} }}

  /* ── Responsive ── */
  @media (max-width: 768px) {{
    .block-container {{ padding:0.3rem 0.5rem 0.3rem 0.5rem !important }}
    .hdr h1 {{ font-size:0.75rem; letter-spacing:1px }}
    .hdr .info {{ font-size:0.5rem }}
    .stats {{ gap:0.3rem }}
    .st-card {{ min-width: 80px; padding:0.3rem 0.4rem }}
    .st-card .v {{ font-size:1rem }}
    .st-card .l {{ font-size:0.5rem; letter-spacing:1px }}
    .feed {{ font-size:0.55rem; min-width:500px }}
    .feed th, .feed td {{ padding:3px 5px }}
    .plbl {{ font-size:0.5rem; letter-spacing:1.5px }}
  }}

  @media (max-width: 480px) {{
    .hdr {{ flex-direction:column; align-items:flex-start }}
    .stats {{ flex-direction:column }}
    .st-card {{ min-width:unset }}
    .st-card .v {{ font-size:1.1rem }}
  }}
</style>
""", unsafe_allow_html=True)


# ── Plotly helpers ───────────────────────────────────────────────────────────
def base_layout(**kw):
    lo = dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=T["dim"], size=9, family="JetBrains Mono"),
        margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
    )
    lo.update(kw)
    return lo


def show(fig, h=150, **kw):
    fig.update_layout(**{**base_layout(), **kw, "height": h})
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── Data ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_data():
    return pd.read_sql("SELECT * FROM cpd_incidents",
                       create_engine(DATABASE_URL),
                       parse_dates=["date_time", "last_updated"])


df = load_data()

# ═══════════════════════════  UPPER SECTION  ═════════════════════════════════

# ── Header + Theme toggle ───────────────────────────────────────────────────
hdr_left, hdr_right = st.columns([8, 1])
with hdr_left:
    st.markdown(f"""<div class="hdr">
      <h1>◉ CPD INCIDENT DASHBOARD</h1>
      <div class="info"><span class="dot"></span>LIVE &nbsp;│&nbsp; {len(df):,} records &nbsp;│&nbsp;
      last: {df["date_time"].max().strftime("%d %b %Y %H:%M")}</div>
    </div>""", unsafe_allow_html=True)
with hdr_right:
    if st.button("", key="theme_toggle"):
        st.session_state.theme = "light" if is_dark else "dark"
        st.rerun()

st.markdown('<div class="hdr-line"></div>', unsafe_allow_html=True)

# ── Filters ──────────────────────────────────────────────────────────────────
mn, mx = df["date_time"].min().date(), df["date_time"].max().date()
f1, f2 = st.columns([1, 3])
date_range = f1.date_input("d", (mn, mx), min_value=mn, max_value=mx, label_visibility="collapsed")
types = sorted(df["type"].dropna().unique())
sel = f2.multiselect("t", types, default=types, label_visibility="collapsed")

if len(date_range) != 2:
    st.stop()
s, e = date_range
data = df[df["date_time"].dt.date.between(s, e) & df["type"].isin(sel)]
if data.empty:
    st.warning("No data.")
    st.stop()

# ── Stats + Donut ────────────────────────────────────────────────────────────
arrests = int((data["type"] == "ARREST").sum())
peak_h = int(data["hour"].mode().iat[0])
top_off = data["subtype"].mode().iat[0].title()
top_loc = data["location"].mode().iat[0].title()

stat_col, donut_col = st.columns([4, 1])

with stat_col:
    st.markdown(f"""<div class="stats">
      <div class="st-card"><div class="v red">{len(data):,}</div><div class="l">Incidents</div></div>
      <div class="st-card"><div class="v">{arrests:,}</div><div class="l">Arrests</div></div>
      <div class="st-card"><div class="v">{len(data)/max((e-s).days,1):.1f}</div><div class="l">Per Day</div></div>
      <div class="st-card"><div class="v">{peak_h:02d}:00</div><div class="l">Peak Hour</div></div>
      <div class="st-card"><div class="v" style="font-size:0.8rem">{top_off}</div><div class="l">Top Offence</div></div>
      <div class="st-card"><div class="v" style="font-size:0.8rem">{top_loc}</div><div class="l">Hotspot</div></div>
    </div>""", unsafe_allow_html=True)

with donut_col:
    st.markdown('<div class="plbl">▸ Type Breakdown</div>', unsafe_allow_html=True)
    type_counts = data["type"].value_counts().head(6)
    donut_colors = [T["red"], T["red_dim"], "#b91c1c", "#991b1b", "#7f1d1d", T["border"]]
    fig = go.Figure(go.Pie(
        labels=type_counts.index, values=type_counts.values,
        hole=0.65, marker=dict(colors=donut_colors[:len(type_counts)],
                               line=dict(color=T["donut_line"], width=2)),
        textinfo="none",
        hovertemplate="%{label}<br>%{value:,} (%{percent})<extra></extra>",
    ))
    fig.add_annotation(
        text=f"<b>{len(data):,}</b><br><span style='font-size:8px;color:{T['dim']}'>total</span>",
        showarrow=False, font=dict(size=13, color=T["txt"]))
    show(fig, h=120)

# ═══════════════════════════  CHART ROWS  ════════════════════════════════════

# ── Row 1: Weekly Trend │ By Hour ────────────────────────────────────────────
left1, right1 = st.columns(2)

with left1:
    st.markdown('<div class="plbl">▸ Weekly Trend</div>', unsafe_allow_html=True)
    w = data.set_index("date_time").resample("W").size().rename("n").reset_index()
    fig = go.Figure(go.Scatter(
        x=w["date_time"], y=w["n"], mode="lines",
        line=dict(color=T["red"], width=1.5),
        fill="tozeroy", fillcolor=T["chart_fill"],
        hovertemplate="%{x|%b %d, %Y}<br>%{y} incidents<extra></extra>",
    ))
    fig.update_xaxes(showgrid=False, color=T["dim"], tickfont_size=7)
    fig.update_yaxes(showgrid=True, gridcolor=T["chart_grid"], griddash="dot",
                     color=T["dim"], tickfont_size=7)
    show(fig, h=180)

with right1:
    st.markdown('<div class="plbl">▸ By Hour</div>', unsafe_allow_html=True)
    hr = data.groupby("hour").size().reindex(range(24), fill_value=0)
    fig = go.Figure(go.Bar(
        x=list(range(24)), y=hr.values,
        marker=dict(color=[T["red"] if v == hr.max() else T["red_dim"] for v in hr.values],
                    line_width=0),
        hovertemplate="%{x}:00 — %{y:,} incidents<extra></extra>",
    ))
    fig.update_xaxes(showgrid=False, color=T["dim"], tickfont_size=7, dtick=2,
                     ticktext=[f"{h:02d}" for h in range(0, 24, 2)],
                     tickvals=list(range(0, 24, 2)))
    fig.update_yaxes(showgrid=True, gridcolor=T["chart_grid"], griddash="dot",
                     color=T["dim"], tickfont_size=7)
    show(fig, h=180)

# ── Row 2: By Day │ Heatmap ─────────────────────────────────────────────────
left2, right2 = st.columns(2)

with left2:
    st.markdown('<div class="plbl">▸ By Day</div>', unsafe_allow_html=True)
    dw = data["day_of_week"].value_counts().reindex(DAY_ORDER_FULL, fill_value=0)
    fig = go.Figure(go.Bar(
        x=DAY_ABBR, y=dw.values,
        marker=dict(color=[T["red"] if v == dw.max() else T["red_dim"] for v in dw.values],
                    line_width=0),
        hovertemplate="%{x}: %{y:,} incidents<extra></extra>",
    ))
    fig.update_xaxes(showgrid=False, color=T["dim"], tickfont_size=8)
    fig.update_yaxes(showgrid=True, gridcolor=T["chart_grid"], griddash="dot",
                     color=T["dim"], tickfont_size=7)
    show(fig, h=180)

with right2:
    st.markdown('<div class="plbl">▸ Heatmap (Day × Hour)</div>', unsafe_allow_html=True)
    ht = pd.crosstab(data["day_of_week"], data["hour"]).reindex(
        index=DAY_ORDER_FULL, columns=range(24), fill_value=0)
    fig = go.Figure(go.Heatmap(
        z=ht.values, x=list(range(24)), y=DAY_ABBR,
        colorscale=[[0, T["heat_base"]], [0.3, T["red_dim"]], [0.7, T["red"]], [1, T["red_glow"]]],
        showscale=False, xgap=1, ygap=1,
        hovertemplate="Hour %{x}:00 · %{y}<br>%{z} incidents<extra></extra>",
    ))
    fig.update_xaxes(showgrid=False, color=T["dim"], tickfont_size=7, dtick=3)
    fig.update_yaxes(color=T["dim"], tickfont_size=8, autorange="reversed")
    show(fig, h=180)

# ═══════════════════════════  INCIDENT FEED (full width) ═════════════════════

st.markdown('<div class="plbl" style="margin-top:0.4rem">▸ Live Incident Feed</div>',
            unsafe_allow_html=True)

recent = data.sort_values("date_time", ascending=False).head(25)
rows = ""
for _, r in recent.iterrows():
    bcls = "badge-a" if r["type"] == "ARREST" else "badge-o"
    badge = f'<span class="badge {bcls}">{r["type"]}</span>'
    dt = r["date_time"].strftime("%d %b %Y &nbsp;%H:%M")
    sub = str(r["subtype"]).title() if pd.notna(r["subtype"]) else "—"
    loc = str(r["location"]).title() if pd.notna(r["location"]) else "—"
    desc = str(r["description"]) if pd.notna(r["description"]) else "—"
    if len(desc) > 100:
        desc = desc[:98] + "…"
    rows += f"<tr><td>{dt}</td><td>{badge}</td><td>{sub}</td><td>{loc}</td><td>{desc}</td></tr>\n"

st.markdown(f"""<div class="feed-wrap"><table class="feed">
<thead><tr><th>Date / Time</th><th>Type</th><th>Offence</th><th>Location</th><th>Description</th></tr></thead>
<tbody>{rows}</tbody></table></div>""", unsafe_allow_html=True)
