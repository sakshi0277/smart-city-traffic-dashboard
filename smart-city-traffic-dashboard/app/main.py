"""Home page of the dashboard. Run with:  streamlit run app/main.py

Premium dark-mode overview page for the Varanasi Traffic Dashboard.

IMPORTANT HONESTY NOTE
----------------------
No free, open live-traffic feed exists for Varanasi. Every congestion number
on this page comes from a small *simulation* written in this file, built on
stated assumptions. It is labelled SIMULATED everywhere and is NOT live traffic.
"""

import sys
from pathlib import Path

# Streamlit only adds the app/ folder to Python's search path.
# We add the project root so that "from src..." imports work.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from src.config import load_config  # noqa: E402

cfg = load_config()

# set_page_config must be the first Streamlit command on the page.
st.set_page_config(
    page_title=cfg["project"]["title"],
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# 1. DESIGN TOKENS (colours used everywhere, so the look stays consistent)
# =============================================================================
CYAN = "#00e5ff"
BLUE = "#3d8bff"       # close to the primaryColor family in .streamlit/config.toml
AMBER = "#ffb020"
RED = "#ff4d6d"
TEXT = "#e6f1ff"
MUTED = "#8fa3c2"

# Congestion levels: (upper limit of index, label, colour)
LEVELS = [
    (30, "Free flow", CYAN),
    (55, "Moderate", BLUE),
    (75, "Heavy", AMBER),
    (101, "Severe", RED),
]


def level_of(index: float) -> tuple[str, str]:
    """Return (label, colour) for a congestion index between 0 and 100."""
    for limit, label, colour in LEVELS:
        if index < limit:
            return label, colour
    return LEVELS[-1][1], LEVELS[-1][2]


# =============================================================================
# 2. CSS: glassmorphism cards, dark background, sidebar, responsive tweaks
# =============================================================================
def inject_css() -> None:
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp {{
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
}}
.stApp {{
    color-scheme: dark;
    color: {TEXT};
    background:
        radial-gradient(1100px 600px at 12% -10%, rgba(0,229,255,0.14), transparent 60%),
        radial-gradient(900px 600px at 100% 0%, rgba(61,139,255,0.16), transparent 55%),
        linear-gradient(180deg, #050b1a 0%, #030712 100%);
}}
[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 2rem; padding-bottom: 3rem; max-width: 1400px; }}
.stApp p, .stApp label, .stApp li, .stApp span {{ color: {TEXT}; }}
[data-testid="stWidgetLabel"] p {{ color: {MUTED}; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; font-size: .72rem; }}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, rgba(8,18,40,.96), rgba(3,7,18,.98));
    border-right: 1px solid rgba(0,229,255,0.15);
}}
.brand {{ display:flex; align-items:center; gap:.7rem; margin:.2rem 0 1.2rem 0; }}
.brand .logo {{
    width:42px; height:42px; border-radius:12px; display:flex; align-items:center;
    justify-content:center; font-size:1.4rem;
    background: linear-gradient(135deg, {CYAN}, {BLUE});
    box-shadow: 0 0 18px rgba(0,229,255,.45);
}}
.brand .name {{ font-weight:800; line-height:1.1; font-size:1rem; }}
.brand .sub {{ color:{MUTED}; font-size:.72rem; }}
.nav-title {{ color:{MUTED}; font-size:.7rem; font-weight:700; letter-spacing:.12em;
    text-transform:uppercase; margin:1rem 0 .4rem 0; }}
.nav-item {{ display:flex; align-items:center; justify-content:space-between;
    padding:.5rem .7rem; border-radius:10px; margin-bottom:.25rem; font-size:.88rem;
    border:1px solid transparent; }}
.nav-item.active {{ background: rgba(0,229,255,.12); border-color: rgba(0,229,255,.35);
    box-shadow: inset 3px 0 0 {CYAN}; font-weight:600; }}
.nav-item.planned {{ opacity:.55; }}
.chip {{ font-size:.62rem; padding:2px 8px; border-radius:999px; font-weight:700;
    letter-spacing:.05em; }}
.chip.now {{ background:rgba(0,229,255,.18); color:{CYAN}; }}
.chip.soon {{ background:rgba(143,163,194,.16); color:{MUTED}; }}

/* ---------- Hero ---------- */
.hero-title {{ font-size:2.3rem; font-weight:800; letter-spacing:-.02em; margin:0;
    background: linear-gradient(90deg, #ffffff 0%, {CYAN} 60%, {BLUE} 100%);
    -webkit-background-clip:text; background-clip:text; color:transparent !important; }}
.hero-sub {{ color:{MUTED}; margin:.3rem 0 .9rem 0; font-size:1rem; }}
.badge {{ display:inline-block; padding:4px 12px; border-radius:999px; font-size:.7rem;
    font-weight:700; letter-spacing:.06em; margin-right:.4rem; margin-bottom:.3rem; }}
.badge.sim {{ background:rgba(255,176,32,.14); color:{AMBER}; border:1px solid rgba(255,176,32,.45); }}
.badge.notlive {{ background:rgba(255,77,109,.12); color:{RED}; border:1px solid rgba(255,77,109,.45); }}
.badge.ver {{ background:rgba(61,139,255,.14); color:{BLUE}; border:1px solid rgba(61,139,255,.45); }}

/* ---------- Glass cards ---------- */
.glass {{
    background: rgba(255,255,255,0.045);
    backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
    border: 1px solid rgba(0,229,255,0.18);
    border-radius: 18px; padding: 1.1rem 1.2rem;
    box-shadow: 0 8px 32px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.06);
    transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
}}
.glass:hover {{ transform: translateY(-3px); border-color: rgba(0,229,255,.5);
    box-shadow: 0 12px 36px rgba(0,229,255,.14); }}
.kpi-top {{ display:flex; justify-content:space-between; align-items:center; }}
.kpi-label {{ color:{MUTED}; font-size:.72rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; }}
.kpi-icon {{ font-size:1.3rem; }}
.kpi-value {{ font-size:2.1rem; font-weight:800; margin:.35rem 0 .1rem 0; line-height:1.1; }}
.kpi-sub {{ color:{MUTED}; font-size:.8rem; }}
.pill {{ display:inline-block; padding:2px 10px; border-radius:999px; font-size:.7rem;
    font-weight:700; margin-left:.4rem; vertical-align:middle; }}
.tag-sim {{ display:inline-block; margin-top:.6rem; font-size:.62rem; font-weight:800;
    letter-spacing:.08em; color:{AMBER}; background:rgba(255,176,32,.12);
    border:1px solid rgba(255,176,32,.4); border-radius:6px; padding:1px 7px; }}

.section-title {{ font-size:1.15rem; font-weight:700; margin:1.6rem 0 .2rem 0; }}
.section-note {{ color:{MUTED}; font-size:.82rem; margin-bottom:.6rem; }}
.notice {{ border-left:4px solid {AMBER}; background:rgba(255,176,32,.08);
    border-radius:10px; padding:.7rem 1rem; font-size:.88rem; margin:.4rem 0 1rem 0; }}
.legend-card {{ border-left:5px solid var(--c); }}
.legend-card b {{ font-size:.95rem; }}
.legend-card div {{ color:{MUTED}; font-size:.8rem; margin-top:.2rem; }}

/* ---------- Responsive ---------- */
@media (max-width: 768px) {{
    .hero-title {{ font-size:1.6rem; }}
    .kpi-value {{ font-size:1.6rem; }}
    .block-container {{ padding-left:1rem; padding-right:1rem; }}
}}
</style>
""",
        unsafe_allow_html=True,
    )


# =============================================================================
# 3. SIMULATED SAMPLE DATA (clearly NOT live traffic)
# =============================================================================
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Real locality names in Varanasi. The multipliers are OUR ASSUMPTIONS
# (e.g. narrow lanes and markets near the ghats -> higher congestion).
# They are not measured values.
ZONES = {
    "Godowlia / Dashashwamedh": 1.25,
    "Lanka (BHU)": 1.10,
    "Cantonment": 1.05,
    "Sigra": 1.00,
    "Rathyatra": 0.95,
    "Kachehri": 0.95,
    "Assi Ghat": 0.90,
    "Maduadih": 0.85,
    "Pandeypur": 0.80,
    "Sarnath": 0.70,
}


def _bump(hour: np.ndarray, centre: float, width: float) -> np.ndarray:
    """A smooth hill shape: used to create rush-hour peaks."""
    return np.exp(-((hour - centre) ** 2) / (2 * width**2))


def _daily_profile(is_weekend: bool) -> np.ndarray:
    """Typical congestion shape over 24 hours (0-100 scale)."""
    h = np.arange(24, dtype=float)
    if is_weekend:
        # Assumption: softer morning, busier late morning and evening.
        return 10 + 30 * _bump(h, 11, 2.5) + 45 * _bump(h, 18.5, 2.5)
    # Assumption: morning peak ~9h, midday bump, strong evening peak ~18h.
    return 12 + 52 * _bump(h, 9, 1.6) + 25 * _bump(h, 13, 2.0) + 58 * _bump(h, 18, 1.9)


@st.cache_data(show_spinner=False)
def build_simulation() -> pd.DataFrame:
    """Create one row per (zone, day, hour) with a SIMULATED congestion index.

    A fixed random seed makes the numbers identical on every run.
    """
    rng = np.random.default_rng(42)
    rows = []
    for zone, factor in ZONES.items():
        for d, day in enumerate(DAYS):
            profile = _daily_profile(is_weekend=d >= 5)
            day_factor = {4: 1.04, 6: 0.92}.get(d, 1.0)  # Friday a bit busier, Sunday calmer
            values = profile * factor * day_factor + rng.normal(0, 3, 24)
            for hour, value in enumerate(np.clip(values, 0, 100)):
                rows.append((zone, day, hour, round(float(value), 1)))
    return pd.DataFrame(rows, columns=["zone", "day", "hour", "congestion_index"])


# =============================================================================
# 4. SMALL HTML HELPERS
# =============================================================================
def kpi_card(icon: str, label: str, value: str, sub: str, colour: str, pill: str = "") -> str:
    """Return the HTML for one glass KPI card (written on single lines on purpose)."""
    pill_html = (
        f"<span class='pill' style='background:{colour}22;color:{colour};"
        f"border:1px solid {colour}66'>{pill}</span>"
        if pill
        else ""
    )
    return (
        f"<div class='glass'>"
        f"<div class='kpi-top'><span class='kpi-label'>{label}</span>"
        f"<span class='kpi-icon'>{icon}</span></div>"
        f"<div class='kpi-value' style='color:{colour}'>{value}{pill_html}</div>"
        f"<div class='kpi-sub'>{sub}</div>"
        f"<span class='tag-sim'>SIMULATED</span>"
        f"</div>"
    )


def style_figure(fig: go.Figure, height: int = 340) -> go.Figure:
    """Give every Plotly chart the same transparent dark look."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color=TEXT),
        margin=dict(l=10, r=10, t=40, b=10),
        height=height,
        title=dict(font=dict(size=15)),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.06)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)", zeroline=False)
    return fig


def show_chart(fig: go.Figure) -> None:
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# =============================================================================
# 5. BUILD THE PAGE
# =============================================================================
inject_css()
data = build_simulation()

# ---------------------------- Sidebar ---------------------------------------
# ---------------------------- Sidebar ---------------------------------------
with st.sidebar:

    # Brand
    st.markdown(
        "<div class='brand'><div class='logo'>🚦</div><div>"
        "<div class='name'>Varanasi Traffic</div>"
        "<div class='sub'>Route Intelligence</div></div></div>",
        unsafe_allow_html=True,
    )

    # Navigation
    st.markdown(
        "<div class='nav-title'>Navigation</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='nav-item active'>"
        "<span>🏠 Overview</span><span class='chip now'>HERE</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.page_link("pages/1_Traffic_Map.py", label="Traffic Map", icon="🗺️")
    st.page_link("pages/2_Route_Comparison.py", label="Route Comparison", icon="🧭")
    st.page_link("pages/3_road_closures.py", label="Closures & Construction", icon="🚧")
    st.page_link("pages/4_transport_intelligence.py", label="Transport Intelligence", icon="🚌")
    st.page_link("pages/5_weather_intelligence.py", label="Weather Intelligence", icon="⛅")
    st.page_link("pages/6_ai_traffic_prediction.py", label="AI Traffic Prediction", icon="🤖")

    # Existing day and hour controls
    st.markdown("<div class='nav-title'>Explore a typical day</div>", unsafe_allow_html=True)
    day = st.selectbox("Day of week", DAYS, index=1)
    hour = st.slider("Hour of day", 0, 23, 9, format="%d:00")
    st.caption("Modelled scenario from a simulation. Not the current time and not live traffic.")
# ---------------------------- Hero ------------------------------------------
st.markdown(
    f"<h1 class='hero-title'>{cfg['project']['title']}</h1>"
    f"<div class='hero-sub'>📍 {cfg['project']['subtitle']} &nbsp;·&nbsp; Entire city coverage</div>"
    f"<span class='badge sim'>SIMULATED SAMPLE DATA</span>"
    f"<span class='badge notlive'>NOT LIVE TRAFFIC</span>"
    f"<span class='badge ver'>v{cfg['project']['version']}</span>",
    unsafe_allow_html=True,
)

st.markdown(
    "<div class='notice'><b>Please read:</b> there is no free, open live-traffic feed for "
    "Varanasi. All congestion figures on this page come from a <b>simulation</b> based on "
    "stated assumptions (rush-hour patterns and area multipliers). They are "
    "<b>never</b> live or real-time traffic.</div>",
    unsafe_allow_html=True,
)# ---------------------------- KPI numbers -----------------------------------
day_data = data[data["day"] == day]
city_by_hour = day_data.groupby("hour")["congestion_index"].mean()
now_slice = day_data[day_data["hour"] == hour].sort_values("congestion_index", ascending=False)

city_index = float(now_slice["congestion_index"].mean())
city_label, city_colour = level_of(city_index)
peak_hour = int(city_by_hour.idxmax())
peak_value = float(city_by_hour.max())
busiest = now_slice.iloc[0]
b_label, b_colour = level_of(float(busiest["congestion_index"]))
heavy_count = int((now_slice["congestion_index"] >= 55).sum())

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(
        kpi_card("🚦", "City congestion index", f"{city_index:.0f}", f"{day} at {hour:02d}:00 · scale 0-100",
                 city_colour, city_label),
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        kpi_card("⏰", f"Typical peak hour ({day})", f"{peak_hour:02d}:00", f"City-wide index about {peak_value:.0f}", CYAN),
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        kpi_card("📍", "Busiest area at this hour", busiest["zone"].split(" / ")[0].split(" (")[0],
                 f"Index {busiest['congestion_index']:.0f} · {b_label}", b_colour),
        unsafe_allow_html=True,
    )
with k4:
    st.markdown(
        kpi_card("⚠️", "Areas heavy or severe", f"{heavy_count} / {len(ZONES)}",
                 "Index of 55 or more at this hour", AMBER if heavy_count else CYAN),
        unsafe_allow_html=True,
    )

# ---------------------------- Row 1: gauge + daily curve --------------------
st.markdown("<div class='section-title'>📈 Traffic overview (simulated)</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='section-note'>Change the day and hour in the sidebar to explore the modelled pattern.</div>",
    unsafe_allow_html=True,
)

c1, c2 = st.columns([1, 2])
with c1:
    gauge = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=city_index,
            number=dict(font=dict(size=44, color=city_colour)),
            title=dict(text=f"Simulated city index · {city_label}", font=dict(size=14)),
            gauge=dict(
                axis=dict(range=[0, 100], tickcolor=MUTED),
                bar=dict(color=city_colour, thickness=0.28),
                bgcolor="rgba(255,255,255,0.03)",
                borderwidth=0,
                steps=[
                    dict(range=[0, 30], color="rgba(0,229,255,0.18)"),
                    dict(range=[30, 55], color="rgba(61,139,255,0.18)"),
                    dict(range=[55, 75], color="rgba(255,176,32,0.18)"),
                    dict(range=[75, 100], color="rgba(255,77,109,0.2)"),
                ],
            ),
        )
    )
    show_chart(style_figure(gauge, 340))

with c2:
    week_avg = data.groupby("hour")["congestion_index"].mean()
    line = go.Figure()
    line.add_trace(go.Scatter(
        x=city_by_hour.index, y=city_by_hour.values, name=f"{day} (simulated)",
        mode="lines", line=dict(color=CYAN, width=3, shape="spline"),
        fill="tozeroy", fillcolor="rgba(0,229,255,0.10)",
    ))
    line.add_trace(go.Scatter(
        x=week_avg.index, y=week_avg.values, name="Weekly average (simulated)",
        mode="lines", line=dict(color=BLUE, width=2, dash="dot", shape="spline"),
    ))
    line.add_vline(x=hour, line_color=AMBER, line_dash="dash",
                   annotation_text=f"{hour:02d}:00", annotation_font_color=AMBER)
    line.update_layout(
        title="City-wide congestion across the day (SIMULATED)",
        xaxis=dict(title="Hour of day", dtick=3),
        yaxis=dict(title="Congestion index", range=[0, 100]),
        legend=dict(orientation="h", y=-0.25),
    )
    show_chart(style_figure(line, 340))

# ---------------------------- Row 2: areas + heatmap ------------------------
c3, c4 = st.columns(2)
with c3:
    ranked = now_slice.sort_values("congestion_index")
    colours = [level_of(v)[1] for v in ranked["congestion_index"]]
    bars = go.Figure(go.Bar(
        x=ranked["congestion_index"], y=ranked["zone"], orientation="h",
        marker=dict(color=colours, line=dict(width=0)),
        text=[f"{v:.0f}" for v in ranked["congestion_index"]], textposition="outside",
        hovertemplate="%{y}<br>Simulated index: %{x:.0f}<extra></extra>",
    ))
    bars.update_layout(
        title=f"Congestion by area · {day} {hour:02d}:00 (SIMULATED)",
        xaxis=dict(range=[0, 110], title="Congestion index"),
    )
    show_chart(style_figure(bars, 400))

with c4:
    pivot = data.groupby(["day", "hour"])["congestion_index"].mean().unstack("hour").reindex(DAYS)
    heat = go.Figure(go.Heatmap(
        z=pivot.values, x=list(pivot.columns), y=list(pivot.index),
        colorscale=[[0, "#06142e"], [0.3, BLUE], [0.6, CYAN], [0.8, AMBER], [1, RED]],
        zmin=0, zmax=100, colorbar=dict(title="Index"),
        hovertemplate="%{y} %{x}:00<br>Simulated index: %{z:.0f}<extra></extra>",
    ))
    heat.update_layout(
        title="Weekly rhythm: day × hour (SIMULATED)",
        xaxis=dict(title="Hour of day", dtick=3),
        yaxis=dict(autorange="reversed"),
    )
    show_chart(style_figure(heat, 400))

# ---------------------------- Data labels (original feature) ----------------
st.markdown("<div class='section-title'>🏷️ How we label every piece of data</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='section-note'>Traffic values in this project are <b>never presented as live</b>. "
    "Every dataset carries one of these labels:</div>",
    unsafe_allow_html=True,
)
cols = st.columns(4)
for col, (name, info) in zip(cols, cfg["provenance"].items()):
    with col:
        st.markdown(
            f"<div class='glass legend-card' style='--c:{info['color']}'>"
            f"<b>{info['emoji']} {name}</b><div>{info['meaning']}</div></div>",
            unsafe_allow_html=True,
        )

# ---------------------------- Map centre (original feature) -----------------
st.markdown("<div class='section-title'>📌 Map centre (from config.yaml)</div>", unsafe_allow_html=True)
st.markdown(
    f"<div class='glass'><b>{cfg['city']['name']}</b> at latitude "
    f"<b style='color:{CYAN}'>{cfg['city']['center_lat']}</b>, longitude "
    f"<b style='color:{CYAN}'>{cfg['city']['center_lon']}</b>"
    f"<div class='kpi-sub'>Interactive maps arrive in a later phase.</div></div>",
    unsafe_allow_html=True,
)

# ---------------------------- Footer ----------------------------------------
st.markdown(
    f"<div class='kpi-sub' style='margin-top:1.5rem;text-align:center'>"
    f"Charts on this page: SIMULATED sample data · Place names: real Varanasi localities · "
    f"Area multipliers: project assumptions · Map data will come from © OpenStreetMap contributors"
    f"</div>",
    unsafe_allow_html=True,
)
st.info("Tip: the look of this page is dark by design. Theme options are in the ⋮ menu → Settings.")