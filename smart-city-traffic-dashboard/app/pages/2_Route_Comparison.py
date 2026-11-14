"""Module 3: Route Comparison & Shortest Route Analysis.

DATA LABELS
  * REAL       road geometry and road distances (OpenStreetMap, via OSMnx)
  * ESTIMATED  travel times (assumed average speeds, NOT live traffic)
  * SIMULATED  optional congestion delay (our simulation, NOT live traffic)

The routing logic lives in src/routing.py. This file only builds the page.
Run the dashboard with:  streamlit run app/main.py
"""

import sys
from pathlib import Path

# This file lives in app/pages/, so the project root is two folders up.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import folium  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402
from streamlit_folium import st_folium  # noqa: E402

from src import routing as rt  # noqa: E402
from src import ui_theme as ui  # noqa: E402
from src.config import get_path, load_config  # noqa: E402
from src.locations import LOCATIONS  # noqa: E402
from src.traffic_simulator import DAYS, build_simulation, city_index  # noqa: E402

cfg = load_config()

st.set_page_config(
    page_title=f"Route Comparison | {cfg['project']['title']}",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)
ui.inject_css()

# =============================================================================
# Constants
# =============================================================================
ROADS_FILE = get_path("raw") / "varanasi_major_roads.geojson"  # from the Traffic Map page
MODES = {"🚗 Car": "drive", "🚶 Walking": "walk"}
ROUTE_COLOURS = {
    "shortest": ui.CYAN, "shortest_fastest": ui.CYAN, "fastest": ui.VIOLET,
    "alt1": ui.GREEN, "alt2": ui.PINK, "alt3": "#c6ff4d",
}
WARN_SNAP_M = 400     # warn if a place is further than this from a road
MAX_SNAP_M = 2000     # refuse if a place is further than this from any road


# =============================================================================
# Cached helpers (so a graph is read from disk once, not on every click)
# =============================================================================
def _stamp(mode: str) -> float:
    """File modification time; changes when the graph is re-downloaded."""
    f = rt.graph_file(mode)
    return f.stat().st_mtime if f.exists() else 0.0


@st.cache_resource(show_spinner=False)
def get_road_graph(mode: str, stamp: float):
    return rt.load_road_graph(mode)


@st.cache_data(show_spinner=False)
def get_simulation():
    return build_simulation()


@st.cache_data(show_spinner=False)
def get_routes(_rg, mode: str, origin_node, dest_node, n_alt: int, stamp: float):
    # Arguments starting with "_" are not hashed by Streamlit (the graph is large).
    return rt.find_routes(_rg, origin_node, dest_node, max_alternatives=n_alt)


def fmt_duration(seconds: float) -> str:
    minutes = seconds / 60
    if minutes < 1:
        return "< 1 min"
    if minutes < 60:
        return f"{minutes:.0f} min"
    return f"{int(minutes // 60)} h {int(minutes % 60):02d} min"


def swap_places() -> None:
    st.session_state.origin, st.session_state.dest = st.session_state.dest, st.session_state.origin


# =============================================================================
# Sidebar controls
# =============================================================================
names = list(LOCATIONS)
st.session_state.setdefault("origin", "Cantonment")
st.session_state.setdefault("dest", "Assi Ghat")

with st.sidebar:
    st.markdown("<div class='nav-title'>Trip</div>", unsafe_allow_html=True)
    mode_label = st.radio("Travel mode", list(MODES), horizontal=True)
    mode = MODES[mode_label]
    origin = st.selectbox("Start", names, key="origin")
    dest = st.selectbox("Destination", names, key="dest")
    st.button("⇅ Swap start and destination", on_click=swap_places)

    st.markdown("<div class='nav-title'>Options</div>", unsafe_allow_html=True)
    n_alt = st.slider("Alternative routes to look for", 0, 3, 2)

    use_sim = False
    sim_day, sim_hour = "Tue", 9
    if mode == "drive":
        use_sim = st.checkbox("Add SIMULATED congestion delay", value=False)
        if use_sim:
            sim_day = st.selectbox("Day of week", DAYS, index=1)
            sim_hour = st.slider("Hour of day", 0, 23, 9, format="%d:00")
            st.caption("Uses our simulation, not live traffic. One city-wide factor is applied equally to every route.")

    st.markdown("<div class='nav-title'>Road networks on disk</div>", unsafe_allow_html=True)
    for label, m in MODES.items():
        st.caption(f"{label}: " + ("✅ downloaded" if rt.graph_exists(m) else "⬜ not downloaded"))

# =============================================================================
# Header
# =============================================================================
st.markdown(
    "<h1 class='hero-title'>🧭 Route Comparison</h1>"
    f"<div class='hero-sub'>📍 {cfg['city']['name']}, Uttar Pradesh &nbsp;·&nbsp; "
    "Shortest route and alternatives on the real road network</div>"
    "<span class='badge real'>REAL: OSM ROADS &amp; DISTANCES</span>"
    "<span class='badge est'>ESTIMATED: TRAVEL TIMES</span>"
    "<span class='badge notlive'>NOT LIVE TRAFFIC</span>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='notice'><b>Please read:</b> distances follow actual OpenStreetMap roads (never "
    "straight lines). Travel times are <b>estimates</b> from assumed average speeds. No real-time "
    "traffic is used anywhere on this page, and place positions are approximate.</div>",
    unsafe_allow_html=True,
)

# =============================================================================
# Make sure the routing graph exists (download ONCE, then reuse from disk)
# =============================================================================
if not rt.graph_exists(mode):
    minutes = "2 to 10" if mode == "drive" else "5 to 20"
    st.warning(
        f"The {mode_label} road network has not been downloaded yet. This is a one-time "
        f"download (about {minutes} minutes, internet needed). It is saved in `data/raw/` and "
        "reused every time, so nothing is downloaded again."
    )
    bbox = rt.compute_bbox(ROADS_FILE, LOCATIONS)
    st.caption(
        "Coverage: the area of your saved Traffic Map roads plus all places in the dropdowns "
        f"(west {bbox[0]:.3f}, south {bbox[1]:.3f}, east {bbox[2]:.3f}, north {bbox[3]:.3f})."
    )
    if st.button(f"⬇️ Download {mode_label} network from OpenStreetMap", type="primary"):
        with st.spinner("Downloading from OpenStreetMap... please keep this tab open."):
            try:
                rt.download_graph(mode, bbox)
                get_road_graph.clear()
                st.rerun()
            except Exception as err:  # friendly message instead of a crash
                st.error(
                    "Download failed. Check your internet connection and try again "
                    "(the OpenStreetMap server can be busy).\n\n" f"Technical detail: {err}"
                )
    st.stop()

with st.spinner("Loading the saved road network..."):
    try:
        rg = get_road_graph(mode, _stamp(mode))
    except Exception as err:
        st.error(f"Could not read the saved road network: {err}")
        st.info(f"You can delete `{rt.graph_file(mode).name}` from `data/raw/` and download it again.")
        st.stop()

# =============================================================================
# Snap both places to the road network and validate
# =============================================================================
if origin == dest:
    st.info("Start and destination are the same place. Please choose two different places.")
    st.stop()

o_lat, o_lon = LOCATIONS[origin]
d_lat, d_lon = LOCATIONS[dest]
o_node, o_snap = rt.nearest_node(rg, o_lat, o_lon)
d_node, d_snap = rt.nearest_node(rg, d_lat, d_lon)

for place, snap in ((origin, o_snap), (dest, d_snap)):
    if snap > MAX_SNAP_M:
        st.error(f"**{place}** is {snap / 1000:.1f} km from the nearest road in the downloaded "
                 "network, so a trustworthy route cannot be calculated.")
        st.stop()
    if snap > WARN_SNAP_M:
        st.warning(f"**{place}** is about {snap:.0f} m from the nearest mapped road. "
                   "Its position is approximate, so treat the route ends with care.")

if o_node == d_node:
    st.info("Both places fall on the same road junction, so there is no route to compare. "
            "Choose places that are further apart.")
    st.stop()

try:
    with st.spinner("Calculating routes on the road network..."):
        routes = get_routes(rg, mode, o_node, d_node, n_alt, _stamp(mode))
except rt.RoutingError as err:
    st.error(str(err))
    st.stop()
except Exception as err:
    st.error(f"Something went wrong while calculating the routes: {err}")
    st.stop()

# =============================================================================
# Travel-time estimates
# =============================================================================
mult = 1.0
sim_index = None
if use_sim and mode == "drive":
    sim_index = city_index(get_simulation(), sim_day, sim_hour)
    mult = rt.congestion_multiplier(sim_index)


def est_seconds(route) -> float:
    return route.free_flow_s * mult


short = routes[0]
fastest = next((r for r in routes if r.key == "fastest"), None)
alternatives = [r for r in routes if r.key.startswith("alt")]

# =============================================================================
# KPI cards
# =============================================================================
st.markdown(
    f"<div class='section-note'>Route: <b>{origin}</b> → <b>{dest}</b> · mode: <b>{mode_label}</b> "
    f"· start snapped {o_snap:.0f} m to the nearest road, destination {d_snap:.0f} m</div>",
    unsafe_allow_html=True,
)
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(ui.kpi_card("Shortest route", f"{short.length_km:.2f} km",
                            "Road-network distance", ui.CYAN, "REAL"), unsafe_allow_html=True)
with k2:
    sub = "Assumed average speeds" if mult == 1.0 else f"Assumed speeds × simulated factor {mult:.2f}"
    st.markdown(ui.kpi_card("Est. time (shortest)", fmt_duration(est_seconds(short)), sub,
                            ui.BLUE, "ESTIMATED"), unsafe_allow_html=True)
with k3:
    st.markdown(ui.kpi_card("Routes found", f"{len(routes)}",
                            f"{len(alternatives)} alternative(s) beyond shortest" +
                            (" and fastest" if fastest else ""), ui.GREEN, "REAL"), unsafe_allow_html=True)
with k4:
    if fastest:
        saved = (est_seconds(short) - est_seconds(fastest)) / 60
        extra = fastest.length_km - short.length_km
        st.markdown(ui.kpi_card("Fastest vs shortest", f"−{saved:.0f} min" if saved >= 0.5 else "≈ same time",
                                f"but {extra:+.2f} km distance", ui.VIOLET, "ESTIMATED"), unsafe_allow_html=True)
    else:
        st.markdown(ui.kpi_card("Fastest vs shortest", "Same route",
                                "Shortest is also fastest", ui.VIOLET, "ESTIMATED"), unsafe_allow_html=True)

if mult != 1.0:
    st.markdown(
        f"<div class='notice'>SIMULATED congestion is switched on: city-wide simulated index "
        f"<b>{sim_index:.0f}/100</b> on {sim_day} at {sim_hour:02d}:00 multiplies every estimated "
        f"time by <b>{mult:.2f}</b>. This is an assumption, not live traffic.</div>",
        unsafe_allow_html=True,
    )
if not alternatives and n_alt > 0:
    st.info("No meaningfully different alternative was found for this trip within a 60% detour. "
            "The road network between these places may offer only one sensible way.")

# =============================================================================
# Interactive map
# =============================================================================
st.markdown("<div class='section-title'>🗺️ Route map</div>", unsafe_allow_html=True)
route_names = {r.key: r.label for r in routes}
shown_keys = st.multiselect(
    "Routes shown on the map", list(route_names), default=list(route_names),
    format_func=lambda k: route_names[k],
)
shown = [r for r in routes if r.key in shown_keys]

legend = "".join(
    f"<span><span class='swatch' style='background:{ROUTE_COLOURS[r.key]}'></span>"
    f"{'⭐ ' if r is short else ''}{r.label} · {r.length_km:.2f} km · {fmt_duration(est_seconds(r))} (est.)</span>"
    for r in shown
)
st.markdown(f"<div class='legend glass' style='margin-bottom:.8rem'>{legend or 'No route selected'}</div>",
            unsafe_allow_html=True)


def route_popup(r) -> str:
    diff = r.length_km - short.length_km
    top = max(r.class_m, key=r.class_m.get)
    return (
        f"<div style='font-family:Inter,Segoe UI,sans-serif;min-width:200px'>"
        f"<b style='font-size:14px'>{'⭐ ' if r is short else ''}{r.label}</b><br>"
        f"Distance: <b>{r.length_km:.2f} km</b> <small>(REAL, OSM)</small><br>"
        f"Est. time: <b>{fmt_duration(est_seconds(r))}</b> <small>(ESTIMATED)</small><br>"
        f"Vs shortest: <b>{diff:+.2f} km</b><br>"
        f"Mostly: {top} ({r.class_m[top] / r.length_m * 100:.0f}%)<br>"
        f"<span style='display:inline-block;margin-top:6px;padding:1px 6px;border-radius:4px;"
        f"background:#e8f0ff;color:#1b3a8a;font-size:10px;font-weight:700'>NOT LIVE TRAFFIC</span></div>"
    )


fmap = folium.Map(location=[(o_lat + d_lat) / 2, (o_lon + d_lon) / 2], zoom_start=13,
                  tiles="CartoDB dark_matter", control_scale=True)

# Draw the longer alternatives first so the shortest route ends up on top.
for r in sorted(shown, key=lambda x: x is short):
    colour = ROUTE_COLOURS[r.key]
    group = folium.FeatureGroup(name=f"{'⭐ ' if r is short else ''}{r.label}", show=True)
    tip = f"{r.label}: {r.length_km:.2f} km · {fmt_duration(est_seconds(r))} (estimated)"
    if r is short:  # soft glow underneath the highlighted shortest route
        folium.PolyLine(r.latlons, color=colour, weight=14, opacity=0.22).add_to(group)
    line_style = dict(color=colour, weight=7 if r is short else 4, opacity=0.95 if r is short else 0.8)
    if r is not short:
        line_style["dash_array"] = "9 7"  # alternatives are dashed, the shortest is solid
    folium.PolyLine(
        r.latlons, tooltip=tip, popup=folium.Popup(route_popup(r), max_width=300), **line_style
    ).add_to(group)
    group.add_to(fmap)

o_pt = (rg.graph.nodes[o_node]["lat"], rg.graph.nodes[o_node]["lon"])
d_pt = (rg.graph.nodes[d_node]["lat"], rg.graph.nodes[d_node]["lon"])
folium.Marker(o_pt, tooltip=f"Start: {origin}", icon=folium.Icon(color="green", icon="play")).add_to(fmap)
folium.Marker(d_pt, tooltip=f"Destination: {dest}", icon=folium.Icon(color="red", icon="stop")).add_to(fmap)

all_pts = [p for r in (shown or routes) for p in r.latlons]
fmap.fit_bounds([[min(p[0] for p in all_pts), min(p[1] for p in all_pts)],
                 [max(p[0] for p in all_pts), max(p[1] for p in all_pts)]], padding=(30, 30))
folium.LayerControl(collapsed=True).add_to(fmap)

# returned_objects=[] stops Streamlit from re-running the page on every map click.
st_folium(fmap, height=600, returned_objects=[], key=f"route_map_{mode}_{o_node}_{d_node}_{n_alt}")

# =============================================================================
# Comparison table
# =============================================================================
st.markdown("<div class='section-title'>📋 Route comparison</div>", unsafe_allow_html=True)
rows = []
for r in routes:
    top = max(r.class_m, key=r.class_m.get)
    rows.append({
        "Route": ("⭐ " if r is short else "") + r.label,
        "Route type": r.description,
        "Distance (km)": round(r.length_km, 2),
        "Est. time": fmt_duration(est_seconds(r)),
        "Distance vs shortest (km)": round(r.length_km - short.length_km, 2),
        "Distance vs shortest (%)": round((r.length_km / short.length_km - 1) * 100, 1),
        "Main road type": f"{top} ({r.class_m[top] / r.length_m * 100:.0f}%)",
    })
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
st.caption("⭐ = shortest route by road distance · Distance and geometry: REAL (OpenStreetMap) · "
           "Time: ESTIMATED (not live traffic).")

# =============================================================================
# Charts
# =============================================================================
st.markdown("<div class='section-title'>📊 Route analysis</div>", unsafe_allow_html=True)
labels = [r.label for r in routes]
bar_colours = [ROUTE_COLOURS[r.key] for r in routes]
c1, c2 = st.columns(2)
with c1:
    fig = go.Figure(go.Bar(
        x=labels, y=[round(r.length_km, 2) for r in routes], marker=dict(color=bar_colours),
        text=[f"{r.length_km:.2f}" for r in routes], textposition="outside",
        hovertemplate="%{x}<br>%{y} km<extra></extra>",
    ))
    fig.update_layout(title="Distance in km (REAL, OSM roads)", yaxis=dict(title="km", rangemode="tozero"))
    st.plotly_chart(ui.style_figure(fig, 340), use_container_width=True, config={"displayModeBar": False})
with c2:
    fig = go.Figure(go.Bar(
        x=labels, y=[round(est_seconds(r) / 60, 1) for r in routes], marker=dict(color=bar_colours),
        text=[f"{est_seconds(r) / 60:.0f}" for r in routes], textposition="outside",
        hovertemplate="%{x}<br>%{y} min (estimated)<extra></extra>",
    ))
    fig.update_layout(title="Estimated time in minutes (ESTIMATED)", yaxis=dict(title="min", rangemode="tozero"))
    st.plotly_chart(ui.style_figure(fig, 340), use_container_width=True, config={"displayModeBar": False})

classes = sorted({c for r in routes for c in r.class_m})
fig = go.Figure()
for cls in classes:
    fig.add_trace(go.Bar(
        name=cls, x=labels, y=[round(r.class_m.get(cls, 0) / 1000, 2) for r in routes],
        hovertemplate="%{x}<br>" + cls + ": %{y} km<extra></extra>",
    ))
fig.update_layout(barmode="stack", title="What each route is made of: kilometres by OSM road type (REAL)",
                  yaxis=dict(title="km"), legend=dict(orientation="h", y=-0.2))
st.plotly_chart(ui.style_figure(fig, 360), use_container_width=True, config={"displayModeBar": False})

# =============================================================================
# Method and limitations
# =============================================================================
with st.expander("ℹ️ How this works, data sources and limitations"):
    meta_path = rt.meta_file(mode)
    if meta_path.exists():
        import json
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        st.markdown(
            f"- **REAL data:** {meta.get('source')}, licence {meta.get('licence')}. "
            f"Network type `{meta.get('network_type')}`, {meta.get('nodes'):,} junctions and "
            f"{meta.get('edges'):,} road segments, downloaded on {meta.get('downloaded_on')}."
        )
    st.markdown(
        "- **Routing:** Dijkstra's algorithm in NetworkX on the OSM road graph. *Shortest* minimises road "
        "distance. *Fastest* minimises estimated time. *Alternatives* use the penalty method: roads already "
        "used get a higher cost, the route is recomputed, and it is kept only if it is clearly different "
        "(under 85% shared road) and no more than 60% longer than the shortest route.\n"
        "- **ESTIMATED times:** each road segment gets an assumed average speed by road class "
        "(for example primary 28 km/h, residential 15 km/h; a lower OSM `maxspeed` tag is respected). Walking "
        "uses a constant 5 km/h. These are our assumptions, not measurements.\n"
        "- **Not modelled:** live or historical traffic, traffic signals, turn restrictions, road closures, "
        "public transport, vehicle type. Closures are planned for a later module.\n"
        "- **Car mode** respects one-way tags. **Walking mode** uses the OSM walking network "
        "(footpaths, steps, and roads where walking is allowed). Cycling is not supported.\n"
        "- **OSM quality:** routes are only as complete as OpenStreetMap. Missing lanes or wrong one-way tags "
        "can change results.\n"
        "- **Places** use approximate coordinates and are snapped to the nearest road junction.\n"
        "- Map tiles: © OpenStreetMap contributors © CARTO."
    )
