"""Streamlit dashboard – Cambridge PD daily log. Red/black, command-center style."""
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///cpd_local.db")
DAY_ORDER_FULL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_ABBR = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# ── Colors ───────────────────────────────────────────────────────────────────
BG = "#0a0a0a"
CARD = "#111"
BORDER = "#1e1e1e"
RED = "#dc2626"
RED_DIM = "#7f1d1d"
RED_GLOW = "#ef4444"
TXT = "#d4d4d4"
DIM = "#666"

st.set_page_config(page_title="CPD Dashboard", page_icon="🔴", layout="wide")

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
  .stApp {{ background:{BG}; color:{TXT}; }}
  header[data-testid="stHeader"] {{ display:none }}
  .block-container {{ padding:0.5rem 1rem 0.5rem 1rem !important; max-width:100%!important }}
  section[data-testid="stSidebar"] {{ display:none }}
  [data-testid="stPlotlyChart"] {{ margin:-0.2rem 0 -0.4rem 0 }}

  /* header */
  .hdr {{ display:flex; justify-content:space-between; align-items:center;
          border-bottom:1px solid {RED_DIM}; padding-bottom:0.4rem; margin-bottom:0.5rem }}
  .hdr h1 {{ font-family:'JetBrains Mono',monospace; font-size:1rem; font-weight:700;
             color:{RED}; letter-spacing:2px; margin:0 }}
  .hdr .info {{ font-family:'JetBrains Mono',monospace; font-size:0.6rem; color:{DIM} }}
  .dot {{ display:inline-block; width:6px; height:6px; background:{RED};
          border-radius:50%; box-shadow:0 0 6px {RED}; margin-right:4px;
          animation:pulse 2s infinite }}
  @keyframes pulse {{ 50%{{opacity:.3}} }}

  /* stat strip */
  .stats {{ display:flex; gap:0.5rem; margin-bottom:0.5rem }}
  .st-card {{ flex:1; background:{CARD}; border:1px solid {BORDER}; border-top:2px solid {RED};
              border-radius:4px; padding:0.4rem 0.6rem; text-align:center }}
  .st-card .v {{ font-family:'JetBrains Mono',monospace; font-size:1.3rem; font-weight:700; color:{TXT} }}
  .st-card .v.red {{ color:{RED} }}
  .st-card .l {{ font-family:'JetBrains Mono',monospace; font-size:0.55rem; color:{DIM};
                 text-transform:uppercase; letter-spacing:1.5px; margin-top:2px }}

  /* panel label */
  .plbl {{ font-family:'JetBrains Mono',monospace; font-size:0.6rem; color:{RED};
           text-transform:uppercase; letter-spacing:2px; margin-bottom:0.15rem }}

  /* feed table */
  .feed {{ width:100%; border-collapse:collapse; font-family:'JetBrains Mono',monospace; font-size:0.65rem }}
  .feed th {{ text-align:left; color:{RED}; font-weight:400; border-bottom:1px solid {RED_DIM};
              padding:4px 8px; text-transform:uppercase; letter-spacing:1px; font-size:0.55rem }}
  .feed td {{ padding:4px 8px; border-bottom:1px solid {BORDER}; color:{DIM};
              white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:220px }}
  .feed tr:hover td {{ color:{TXT}; background:{RED_DIM}18 }}
  .badge {{ display:inline-block; padding:1px 6px; border-radius:3px; font-size:0.55rem; font-weight:600 }}
  .badge-a {{ background:{RED_DIM}; color:{RED_GLOW} }}
  .badge-o {{ background:{BORDER}; color:{DIM} }}
</style>
""", unsafe_allow_html=True)

# ── Plotly base ──────────────────────────────────────────────────────────────
LO = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
          font=dict(color=DIM, size=9, family="JetBrains Mono"),
          margin=dict(l=0, r=0, t=0, b=0), showlegend=False)


def show(fig, h=150, **kw):
    fig.update_layout(**{**LO, **kw, "height": h})
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── Data ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_data():
    return pd.read_sql("SELECT * FROM cpd_incidents",
                       create_engine(DATABASE_URL),
                       parse_dates=["date_time", "last_updated"])


df = load_data()

# ═══════════════════════════  UPPER SECTION  ═════════════════════════════════

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown(f"""<div class="hdr">
  <h1>◉ CPD INCIDENT DASHBOARD</h1>
  <div class="info"><span class="dot"></span>LIVE &nbsp;│&nbsp; {len(df):,} records &nbsp;│&nbsp;
  last: {df["date_time"].max().strftime("%d %b %Y %H:%M")}</div>
</div>""", unsafe_allow_html=True)

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
    donut_colors = [RED, RED_DIM, "#b91c1c", "#991b1b", "#7f1d1d", BORDER]
    fig = go.Figure(go.Pie(
        labels=type_counts.index, values=type_counts.values,
        hole=0.65, marker=dict(colors=donut_colors[:len(type_counts)],
                               line=dict(color=BG, width=2)),
        textinfo="none",
        hovertemplate="%{label}<br>%{value:,} (%{percent})<extra></extra>",
    ))
    fig.add_annotation(
        text=f"<b>{len(data):,}</b><br><span style='font-size:8px;color:{DIM}'>total</span>",
        showarrow=False, font=dict(size=13, color=TXT))
    show(fig, h=120)

# ═══════════════════════════  CHART ROWS  ════════════════════════════════════

# ── Row 1: Weekly Trend (left) │ By Hour (right) ────────────────────────────
left1, right1 = st.columns(2)

with left1:
    st.markdown('<div class="plbl">▸ Weekly Trend</div>', unsafe_allow_html=True)
    w = data.set_index("date_time").resample("W").size().rename("n").reset_index()
    fig = go.Figure(go.Scatter(
        x=w["date_time"], y=w["n"], mode="lines",
        line=dict(color=RED, width=1.5),
        fill="tozeroy", fillcolor="rgba(220,38,38,0.08)",
        hovertemplate="%{x|%b %d, %Y}<br>%{y} incidents<extra></extra>",
    ))
    fig.update_xaxes(showgrid=False, color=DIM, tickfont_size=7)
    fig.update_yaxes(showgrid=True, gridcolor=BORDER, griddash="dot", color=DIM, tickfont_size=7)
    show(fig, h=180)

with right1:
    st.markdown('<div class="plbl">▸ By Hour</div>', unsafe_allow_html=True)
    hr = data.groupby("hour").size().reindex(range(24), fill_value=0)
    fig = go.Figure(go.Bar(
        x=list(range(24)), y=hr.values,
        marker=dict(color=[RED if v == hr.max() else RED_DIM for v in hr.values],
                    line_width=0),
        hovertemplate="%{x}:00 — %{y:,} incidents<extra></extra>",
    ))
    fig.update_xaxes(showgrid=False, color=DIM, tickfont_size=7, dtick=2,
                     ticktext=[f"{h:02d}" for h in range(0, 24, 2)],
                     tickvals=list(range(0, 24, 2)))
    fig.update_yaxes(showgrid=True, gridcolor=BORDER, griddash="dot", color=DIM, tickfont_size=7)
    show(fig, h=180)

# ── Row 2: By Day (left) │ Heatmap (right) ──────────────────────────────────
left2, right2 = st.columns(2)

with left2:
    st.markdown('<div class="plbl">▸ By Day</div>', unsafe_allow_html=True)
    dw = data["day_of_week"].value_counts().reindex(DAY_ORDER_FULL, fill_value=0)
    fig = go.Figure(go.Bar(
        x=DAY_ABBR, y=dw.values,
        marker=dict(color=[RED if v == dw.max() else RED_DIM for v in dw.values],
                    line_width=0),
        hovertemplate="%{x}: %{y:,} incidents<extra></extra>",
    ))
    fig.update_xaxes(showgrid=False, color=DIM, tickfont_size=8)
    fig.update_yaxes(showgrid=True, gridcolor=BORDER, griddash="dot", color=DIM, tickfont_size=7)
    show(fig, h=180)

with right2:
    st.markdown('<div class="plbl">▸ Heatmap (Day × Hour)</div>', unsafe_allow_html=True)
    ht = pd.crosstab(data["day_of_week"], data["hour"]).reindex(
        index=DAY_ORDER_FULL, columns=range(24), fill_value=0)
    fig = go.Figure(go.Heatmap(
        z=ht.values, x=list(range(24)), y=DAY_ABBR,
        colorscale=[[0, BG], [0.3, RED_DIM], [0.7, RED], [1, RED_GLOW]],
        showscale=False, xgap=1, ygap=1,
        hovertemplate="Hour %{x}:00 · %{y}<br>%{z} incidents<extra></extra>",
    ))
    fig.update_xaxes(showgrid=False, color=DIM, tickfont_size=7, dtick=3)
    fig.update_yaxes(color=DIM, tickfont_size=8, autorange="reversed")
    show(fig, h=180)

# ═══════════════════════════  INCIDENT FEED  ═════════════════════════════════

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

st.markdown(f"""<table class="feed">
<thead><tr><th>Date / Time</th><th>Type</th><th>Offence</th><th>Location</th><th>Description</th></tr></thead>
<tbody>{rows}</tbody></table>""", unsafe_allow_html=True)
