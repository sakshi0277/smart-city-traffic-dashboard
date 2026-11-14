"""Module 2: Interactive Varanasi Traffic Map.

Shows TWO clearly separated layers:
  * REAL       - major roads downloaded from OpenStreetMap (via OSMnx).
  * SIMULATED  - congestion markers for areas of Varanasi, produced by a small
                 simulation in this file. This is NOT live traffic.

Run the whole dashboard with:  streamlit run app/main.py
Then open "Traffic Map" in the sidebar.
"""

import json
import sys
from datetime import date
from pathlib import Path

# This file lives in app/pages/, so the project root is two folders up.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import folium  # noqa: E402
import geopandas as gpd  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402
from streamlit_folium import st_folium  # noqa: E402

from src.config import get_path, load_config  # noqa: E402

cfg = load_config()

st.set_page_config(
    page_title=f"Traffic Map | {cfg['project']['title']}",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# 1. DESIGN TOKENS (same palette as the Home page)
# =============================================================================
CYAN, BLUE, AMBER, RED = "#00e5ff", "#3d8bff", "#ffb020", "#ff4d6d"
TEXT, MUTED = "#e6f1ff", "#8fa3c2"

# (upper limit of index, label, colour)
LEVELS = [
    (30, "Free flow", CYAN),
    (55, "Moderate", BLUE),
    (75, "Heavy", AMBER),
    (101, "Severe", RED),
]
LEVEL_NAMES = [name for _, name, _ in LEVELS]
LEVEL_COLOUR = {name: colour for _, name, colour in LEVELS}


def level_of(index: float) -> str:
    """Return the level name for a congestion index between 0 and 100."""
    for limit, name, _ in LEVELS:
        if index < limit:
            return name
    return LEVELS[-1][1]


def inject_css() -> None:
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp {{ font-family:'Inter','Segoe UI',system-ui,sans-serif; }}
.stApp {{
    color-scheme: dark; color:{TEXT};
    background:
      radial-gradient(1100px 600px at 12% -10%, rgba(0,229,255,0.14), transparent 60%),
      radial-gradient(900px 600px at 100% 0%, rgba(61,139,255,0.16), transparent 55%),
      linear-gradient(180deg,#050b1a 0%,#030712 100%);
}}
[data-testid="stHeader"] {{ background:transparent; }}
.block-container {{ padding-top:2rem; padding-bottom:3rem; max-width:1400px; }}
.stApp p, .stApp label, .stApp li, .stApp span {{ color:{TEXT}; }}
[data-testid="stWidgetLabel"] p {{ color:{MUTED}; font-weight:600; letter-spacing:.04em;
    text-transform:uppercase; font-size:.72rem; }}
[data-testid="stSidebar"] {{
    background:linear-gradient(180deg,rgba(8,18,40,.96),rgba(3,7,18,.98));
    border-right:1px solid rgba(0,229,255,0.15);
}}
.nav-title {{ color:{MUTED}; font-size:.7rem; font-weight:700; letter-spacing:.12em;
    text-transform:uppercase; margin:1rem 0 .4rem 0; }}
.hero-title {{ font-size:2.1rem; font-weight:800; letter-spacing:-.02em; margin:0;
    background:linear-gradient(90deg,#fff 0%,{CYAN} 60%,{BLUE} 100%);
    -webkit-background-clip:text; background-clip:text; color:transparent !important; }}
.hero-sub {{ color:{MUTED}; margin:.3rem 0 .9rem 0; }}
.badge {{ display:inline-block; padding:4px 12px; border-radius:999px; font-size:.7rem;
    font-weight:700; letter-spacing:.06em; margin-right:.4rem; margin-bottom:.3rem; }}
.badge.real {{ background:rgba(46,125,50,.18); color:#66e08a; border:1px solid rgba(102,224,138,.5); }}
.badge.sim {{ background:rgba(255,176,32,.14); color:{AMBER}; border:1px solid rgba(255,176,32,.45); }}
.badge.notlive {{ background:rgba(255,77,109,.12); color:{RED}; border:1px solid rgba(255,77,109,.45); }}
.glass {{
    background:rgba(255,255,255,0.045); backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px);
    border:1px solid rgba(0,229,255,0.18); border-radius:18px; padding:1.05rem 1.2rem;
    box-shadow:0 8px 32px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.06);
}}
.kpi-label {{ color:{MUTED}; font-size:.72rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; }}
.kpi-value {{ font-size:1.9rem; font-weight:800; margin:.3rem 0 .1rem 0; line-height:1.1; }}
.kpi-sub {{ color:{MUTED}; font-size:.8rem; }}
.tag {{ display:inline-block; margin-top:.5rem; font-size:.62rem; font-weight:800; letter-spacing:.08em;
    border-radius:6px; padding:1px 7px; }}
.tag.real {{ color:#66e08a; background:rgba(46,125,50,.18); border:1px solid rgba(102,224,138,.45); }}
.tag.sim {{ color:{AMBER}; background:rgba(255,176,32,.12); border:1px solid rgba(255,176,32,.4); }}
.section-title {{ font-size:1.1rem; font-weight:700; margin:1.4rem 0 .2rem 0; }}
.section-note {{ color:{MUTED}; font-size:.82rem; margin-bottom:.6rem; }}
.notice {{ border-left:4px solid {AMBER}; background:rgba(255,176,32,.08); border-radius:10px;
    padding:.7rem 1rem; font-size:.88rem; margin:.4rem 0 1rem 0; }}
.legend {{ display:flex; flex-wrap:wrap; gap:.4rem 1.2rem; font-size:.82rem; align-items:center; }}
.dot {{ display:inline-block; width:12px; height:12px; border-radius:50%; margin-right:.4rem; vertical-align:middle; }}
.line {{ display:inline-block; width:22px; height:4px; border-radius:2px; margin-right:.4rem; vertical-align:middle; }}
@media (max-width:768px) {{
  .hero-title {{ font-size:1.5rem; }} .kpi-value {{ font-size:1.5rem; }}
  .block-container {{ padding-left:1rem; padding-right:1rem; }}
}}
</style>
""",
        unsafe_allow_html=True,
    )


# =============================================================================
# 2. SIMULATED TRAFFIC (same model and random seed as the Home page)
# =============================================================================
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# name: (latitude, longitude, multiplier)
# Coordinates are APPROXIMATE centres of well-known localities, used only to
# place the markers. Multipliers are OUR ASSUMPTIONS, not measurements.
AREAS = {
    "Godowlia / Dashashwamedh": (25.3092, 83.0104, 1.25),
    "Lanka (BHU)": (25.2814, 82.9916, 1.10),
    "Cantonment": (25.3270, 82.9880, 1.05),
    "Sigra": (25.3150, 82.9800, 1.00),
    "Rathyatra": (25.3160, 82.9930, 0.95),
    "Kachehri": (25.3337, 82.9847, 0.95),
    "Assi Ghat": (25.2880, 83.0060, 0.90),
    "Maduadih": (25.3380, 82.9600, 0.85),
    "Pandeypur": (25.3450, 82.9650, 0.80),
    "Sarnath": (25.3809, 83.0240, 0.70),
}


def _bump(hour: np.ndarray, centre: float, width: float) -> np.ndarray:
    return np.exp(-((hour - centre) ** 2) / (2 * width**2))


def _daily_profile(is_weekend: bool) -> np.ndarray:
    h = np.arange(24, dtype=float)
    if is_weekend:
        return 10 + 30 * _bump(h, 11, 2.5) + 45 * _bump(h, 18.5, 2.5)
    return 12 + 52 * _bump(h, 9, 1.6) + 25 * _bump(h, 13, 2.0) + 58 * _bump(h, 18, 1.9)


@st.cache_data(show_spinner=False)
def build_simulation() -> pd.DataFrame:
    """One row per (area, day, hour) with a SIMULATED congestion index (0-100)."""
    rng = np.random.default_rng(42)  # fixed seed -> same numbers every run
    rows = []
    for area, (_, _, factor) in AREAS.items():
        for d, day in enumerate(DAYS):
            profile = _daily_profile(is_weekend=d >= 5)
            day_factor = {4: 1.04, 6: 0.92}.get(d, 1.0)
            values = profile * factor * day_factor + rng.normal(0, 3, 24)
            for hour, value in enumerate(np.clip(values, 0, 100)):
                rows.append((area, day, hour, round(float(value), 1)))
    return pd.DataFrame(rows, columns=["area", "day", "hour", "congestion_index"])


# =============================================================================
# 3. REAL DATA: major roads from OpenStreetMap (downloaded once, then cached)
# =============================================================================
# We keep only major road classes. This keeps the map fast and readable.
ROAD_FILTER = (
    '["highway"~"motorway|motorway_link|trunk|trunk_link|primary|primary_link|'
    'secondary|secondary_link|tertiary|tertiary_link"]'
)
ROADS_FILE = get_path("raw") / "varanasi_major_roads.geojson"
META_FILE = get_path("raw") / "varanasi_major_roads_meta.json"

# Road colour shows the ROAD CLASS only. It is deliberately NOT red/amber/green,
# so nobody mistakes it for traffic.
ROAD_STYLE = {
    "motorway": ("#7fd1ff", 3.5),
    "trunk": ("#7fd1ff", 3.5),
    "primary": ("#5aa9ff", 3.0),
    "secondary": ("#4a86d6", 2.2),
    "tertiary": ("#3a65a8", 1.5),
}


def _road_class(value) -> str:
    """OSM sometimes stores a list. Take the first value and drop '_link'."""
    if isinstance(value, (list, tuple)):
        value = value[0]
    return str(value).replace("_link", "")


def download_roads() -> dict:
    """Download major roads for Varanasi from OpenStreetMap and save them to disk."""
    import osmnx as ox  # imported here so the page opens fast when data is cached

    ox.settings.use_cache = True
    ox.settings.log_console = False

    try:
        # Preferred: the official city boundary from OpenStreetMap.
        graph = ox.graph_from_place(
            cfg["city"]["place_query"], custom_filter=ROAD_FILTER, retain_all=True
        )
        source = "place boundary: " + cfg["city"]["place_query"]
    except Exception:
        # Fallback: a 12 km box around the city centre.
        graph = ox.graph_from_point(
            (cfg["city"]["center_lat"], cfg["city"]["center_lon"]),
            dist=12000, custom_filter=ROAD_FILTER, retain_all=True,
        )
        source = "12 km box around the city centre (boundary lookup failed)"

    graph = ox.convert.to_undirected(graph)  # remove the duplicate two-way edges
    edges = ox.graph_to_gdfs(graph, nodes=False).reset_index(drop=True)

    edges["road_class"] = edges["highway"].apply(_road_class)
    edges["name"] = edges["name"].apply(
        lambda v: ", ".join(v) if isinstance(v, list) else (v if isinstance(v, str) else "Unnamed road")
    )
    edges = edges[["name", "road_class", "geometry"]]

    ROADS_FILE.parent.mkdir(parents=True, exist_ok=True)
    edges.to_file(ROADS_FILE, driver="GeoJSON")

    meta = {
        "label": "REAL",
        "source": "OpenStreetMap contributors (via OSMnx " + ox.__version__ + ")",
        "licence": "ODbL 1.0",
        "area_used": source,
        "downloaded_on": date.today().isoformat(),
        "road_segments": int(len(edges)),
    }
    META_FILE.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


@st.cache_data(show_spinner=False)
def load_roads():
    """Read the saved roads. Returns (GeoDataFrame, metadata) or (None, None)."""
    if not ROADS_FILE.exists():
        return None, None
    roads = gpd.read_file(ROADS_FILE)
    meta = json.loads(META_FILE.read_text(encoding="utf-8")) if META_FILE.exists() else {}
    return roads, meta


# =============================================================================
# 4. MAP BUILDER
# =============================================================================
def build_map(roads, areas_df: pd.DataFrame, show_roads: bool) -> folium.Map:
    fmap = folium.Map(
        location=[cfg["city"]["center_lat"], cfg["city"]["center_lon"]],
        zoom_start=cfg["city"]["default_zoom"],
        tiles="CartoDB dark_matter",
        control_scale=True,
    )

    # ---- REAL layer: OSM roads ----
    if show_roads and roads is not None and len(roads) > 0:
        road_layer = folium.FeatureGroup(name="🟢 REAL: OpenStreetMap roads", show=True)
        folium.GeoJson(
            roads.to_json(),
            style_function=lambda f: {
                "color": ROAD_STYLE.get(f["properties"]["road_class"], ("#3a65a8", 1.5))[0],
                "weight": ROAD_STYLE.get(f["properties"]["road_class"], ("#3a65a8", 1.5))[1],
                "opacity": 0.85,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["name", "road_class"], aliases=["Road:", "Class:"]
            ),
        ).add_to(road_layer)
        road_layer.add_to(fmap)

    # ---- SIMULATED layer: congestion markers ----
    marker_layer = folium.FeatureGroup(name="🟡 SIMULATED: congestion markers (not live)", show=True)
    for _, row in areas_df.iterrows():
        colour = LEVEL_COLOUR[row["level"]]
        popup_html = (
            f"<div style='font-family:Inter,Segoe UI,sans-serif;min-width:190px'>"
            f"<b style='font-size:14px'>{row['area']}</b><br>"
            f"Simulated index: <b>{row['congestion_index']:.0f}</b> / 100<br>"
            f"Level: <b style='color:{colour}'>{row['level']}</b><br>"
            f"<span style='display:inline-block;margin-top:6px;padding:1px 6px;border-radius:4px;"
            f"background:#fff3d6;color:#8a5a00;font-size:10px;font-weight:700'>"
            f"SIMULATED · NOT LIVE TRAFFIC</span></div>"
        )
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=9 + row["congestion_index"] / 6,
            color=colour, weight=2, fill=True, fill_color=colour, fill_opacity=0.45,
            tooltip=f"{row['area']}: {row['level']} (simulated {row['congestion_index']:.0f})",
            popup=folium.Popup(popup_html, max_width=260),
        ).add_to(marker_layer)
    marker_layer.add_to(fmap)

    folium.LayerControl(collapsed=False).add_to(fmap)
    return fmap


def kpi(label: str, value: str, sub: str, colour: str, tag: str) -> str:
    tag_html = (
        "<span class='tag real'>REAL</span>" if tag == "REAL" else "<span class='tag sim'>SIMULATED</span>"
    )
    return (
        f"<div class='glass'><div class='kpi-label'>{label}</div>"
        f"<div class='kpi-value' style='color:{colour}'>{value}</div>"
        f"<div class='kpi-sub'>{sub}</div>{tag_html}</div>"
    )


# =============================================================================
# 5. BUILD THE PAGE
# =============================================================================
inject_css()
sim = build_simulation()
roads, roads_meta = load_roads()

# ---------------------------- Sidebar filters --------------------------------
with st.sidebar:
    st.markdown("<div class='nav-title'>Scenario (simulated)</div>", unsafe_allow_html=True)
    day = st.selectbox("Day of week", DAYS, index=1)
    hour = st.slider("Hour of day", 0, 23, 9, format="%d:00")
    st.caption("A modelled typical day. Not the current time and not live traffic.")

    st.markdown("<div class='nav-title'>Filters</div>", unsafe_allow_html=True)
    chosen_levels = st.multiselect("Congestion level", LEVEL_NAMES, default=LEVEL_NAMES)
    chosen_areas = st.multiselect("Area", list(AREAS), default=list(AREAS))

    st.markdown("<div class='nav-title'>Road layer (REAL)</div>", unsafe_allow_html=True)
    show_roads = st.checkbox("Show OpenStreetMap roads", value=True)
    classes_available = ["motorway", "trunk", "primary", "secondary", "tertiary"]
    chosen_classes = st.multiselect("Road classes", classes_available, default=classes_available)

# ---------------------------- Hero ------------------------------------------
st.markdown(
    "<h1 class='hero-title'>🗺️ Interactive Traffic Map</h1>"
    f"<div class='hero-sub'>📍 {cfg['city']['name']}, Uttar Pradesh &nbsp;·&nbsp; Entire city coverage</div>"
    "<span class='badge real'>REAL: OSM ROADS</span>"
    "<span class='badge sim'>SIMULATED: CONGESTION</span>"
    "<span class='badge notlive'>NOT LIVE TRAFFIC</span>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='notice'><b>Please read:</b> the roads come from OpenStreetMap (real). "
    "The congestion circles are a <b>simulation</b> built on stated assumptions and are "
    "<b>never</b> live or real-time traffic. Marker positions are approximate locality centres, "
    "and road colours show road class only, not traffic.</div>",
    unsafe_allow_html=True,
)

# ---------------------------- Road data status -------------------------------
if roads is None:
    st.warning(
        "The REAL road layer has not been downloaded yet. The first download takes "
        "about 1 to 5 minutes and needs internet access. It is saved in `data/raw/`, "
        "so you only do it once."
    )
    if st.button("⬇️ Download Varanasi roads from OpenStreetMap", type="primary"):
        with st.spinner("Downloading roads from OpenStreetMap... please wait."):
            try:
                download_roads()
                load_roads.clear()
                st.rerun()
            except Exception as err:  # show a friendly message, not a crash
                st.error(
                    "Download failed. Check your internet connection and try again.\n\n"
                    f"Technical detail: {err}"
                )
else:
    roads_view = roads[roads["road_class"].isin(chosen_classes)]

# ---------------------------- Apply filters ----------------------------------
now = sim[(sim["day"] == day) & (sim["hour"] == hour)].copy()
now["lat"] = now["area"].map(lambda a: AREAS[a][0])
now["lon"] = now["area"].map(lambda a: AREAS[a][1])
now["level"] = now["congestion_index"].map(level_of)
shown = now[now["level"].isin(chosen_levels) & now["area"].isin(chosen_areas)]

# ---------------------------- KPI cards --------------------------------------
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(kpi("Areas shown", f"{len(shown)} / {len(AREAS)}", f"{day} at {hour:02d}:00", CYAN, "SIM"),
                unsafe_allow_html=True)
with k2:
    avg = shown["congestion_index"].mean() if len(shown) else float("nan")
    lvl = level_of(avg) if len(shown) else "-"
    st.markdown(kpi("Average index (shown)", "-" if not len(shown) else f"{avg:.0f}",
                    lvl, LEVEL_COLOUR.get(lvl, MUTED), "SIM"), unsafe_allow_html=True)
with k3:
    if len(shown):
        worst = shown.sort_values("congestion_index", ascending=False).iloc[0]
        st.markdown(kpi("Busiest area (shown)", worst["area"].split(" / ")[0].split(" (")[0],
                        f"Index {worst['congestion_index']:.0f} · {worst['level']}",
                        LEVEL_COLOUR[worst["level"]], "SIM"), unsafe_allow_html=True)
    else:
        st.markdown(kpi("Busiest area (shown)", "-", "No areas match the filters", MUTED, "SIM"),
                    unsafe_allow_html=True)
with k4:
    if roads is not None:
        st.markdown(kpi("Road segments loaded", f"{len(roads):,}",
                        f"Downloaded {roads_meta.get('downloaded_on', 'unknown date')}", "#66e08a", "REAL"),
                    unsafe_allow_html=True)
    else:
        st.markdown(kpi("Road segments loaded", "0", "Download pending", MUTED, "REAL"),
                    unsafe_allow_html=True)

# ---------------------------- Legend + map -----------------------------------
st.markdown("<div class='section-title'>🧭 Map</div>", unsafe_allow_html=True)
legend = "".join(
    f"<span><span class='dot' style='background:{c}'></span>{n} (simulated)</span>"
    for n, c in LEVEL_COLOUR.items()
)
st.markdown(
    f"<div class='legend glass' style='margin-bottom:.8rem'>{legend}"
    f"<span><span class='line' style='background:#5aa9ff'></span>OSM road (REAL, colour = class)</span></div>",
    unsafe_allow_html=True,
)

if len(shown) == 0:
    st.warning("No areas match the current filters. Showing the map without congestion markers.")

fmap = build_map(roads_view if roads is not None else None, shown, show_roads)
# returned_objects=[] stops Streamlit from re-running the page on every map click.
st_folium(fmap, height=620, returned_objects=[], key="traffic_map")

# ---------------------------- Details ----------------------------------------
st.markdown("<div class='section-title'>📊 Area details (simulated)</div>", unsafe_allow_html=True)
c1, c2 = st.columns([3, 2])
with c1:
    if len(shown):
        ranked = shown.sort_values("congestion_index")
        fig = go.Figure(go.Bar(
            x=ranked["congestion_index"], y=ranked["area"], orientation="h",
            marker=dict(color=[LEVEL_COLOUR[l] for l in ranked["level"]]),
            text=[f"{v:.0f}" for v in ranked["congestion_index"]], textposition="outside",
            hovertemplate="%{y}<br>Simulated index: %{x:.0f}<extra></extra>",
        ))
        fig.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, Segoe UI, sans-serif", color=TEXT),
            title=f"Congestion by area · {day} {hour:02d}:00 (SIMULATED)",
            xaxis=dict(range=[0, 110], title="Congestion index", gridcolor="rgba(255,255,255,0.06)"),
            margin=dict(l=10, r=10, t=40, b=10), height=380,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Nothing to chart for the current filters.")
with c2:
    table = shown[["area", "congestion_index", "level"]].sort_values("congestion_index", ascending=False)
    table.columns = ["Area", "Simulated index", "Level"]
    table["Data label"] = "SIMULATED"
    st.dataframe(table, hide_index=True, use_container_width=True)

# ---------------------------- Data sources -----------------------------------
with st.expander("ℹ️ Data sources and limitations"):
    if roads_meta:
        st.markdown(
            f"- **REAL roads:** {roads_meta.get('source')}, licence {roads_meta.get('licence')}. "
            f"Area used: {roads_meta.get('area_used')}. Downloaded on {roads_meta.get('downloaded_on')}. "
            "Only major road classes are drawn (motorway, trunk, primary, secondary, tertiary)."
        )
    else:
        st.markdown("- **REAL roads:** OpenStreetMap contributors (not downloaded yet).")
    st.markdown(
        "- **SIMULATED congestion:** rush-hour curves plus area multipliers that are our own "
        "assumptions, with small random variation (fixed seed). No traffic sensor, GPS or "
        "commercial traffic feed is used.\n"
        "- **Marker positions** are approximate locality centres, not exact junctions.\n"
        "- Map tiles: © OpenStreetMap contributors © CARTO."
    )