from pathlib import Path
import math

import pandas as pd
import plotly.express as px
import streamlit as st

from src.locations import LOCATIONS

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Transport Intelligence",
    page_icon="🚌",
    layout="wide"
)
# ========== PREMIUM DASHBOARD THEME ==========

st.markdown("""
<style>

/* Main background */
.stApp {
    background: linear-gradient(135deg, #07111f 0%, #101d33 55%, #0b1528 100%);
    color: #eaf4ff;
}

/* Hide default header decoration */
header[data-testid="stHeader"] {
    background: transparent;
}

/* Hero section */
.hero-section {
    padding: 35px 30px;
    border-radius: 20px;
    background: linear-gradient(115deg, #102d50, #123e68, #087e9b);
    border: 1px solid rgba(100, 210, 255, 0.25);
    box-shadow: 0 12px 35px rgba(0, 160, 255, 0.15);
    animation: fadeIn 1s ease-in-out;
    margin-bottom: 25px;
}

.hero-title {
    font-size: 34px;
    font-weight: 800;
    color: white;
    letter-spacing: 0.5px;
}

.hero-subtitle {
    font-size: 15px;
    color: #c5e8ff;
    margin-top: 8px;
}

/* KPI cards */
div[data-testid="stMetric"] {
    background: rgba(20, 47, 75, 0.75);
    border: 1px solid rgba(69, 190, 255, 0.25);
    padding: 20px;
    border-radius: 16px;
    box-shadow: 0 5px 18px rgba(0, 0, 0, 0.2);
    transition: all 0.3s ease;
    animation: fadeIn 0.8s ease-in-out;
}

div[data-testid="stMetric"]:hover {
    transform: translateY(-5px);
    border-color: #38bdf8;
    box-shadow: 0 8px 25px rgba(56, 189, 248, 0.2);
}

div[data-testid="stMetricLabel"] {
    color: #a8d8f5;
}

div[data-testid="stMetricValue"] {
    color: #38d9ff;
    font-weight: 800;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(90deg, #087eae, #06b6d4);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 10px 22px;
    font-weight: 700;
    transition: all 0.3s ease;
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 20px rgba(6, 182, 212, 0.35);
    color: white;
}

/* Section headings */
h1, h2, h3 {
    color: #e5f5ff !important;
}

/* Smooth entrance animation */
@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(15px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* Dividers */
hr {
    border-color: rgba(56, 189, 248, 0.2);
}

</style>
""", unsafe_allow_html=True)


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

TRANSPORT_FILE = RAW_DIR / "varanasi_transport_points.csv"

st.markdown("""
<div class="hero-section">
    <div class="hero-title">
        🚌 TRANSPORT INTELLIGENCE
    </div>
    <div class="hero-subtitle">
        Varanasi Smart City | Intelligent Mobility & Transport Analytics
    </div>
    <div class="hero-subtitle">
        Explore public transport • Compare personal mobility •
        Discover smarter journeys
    </div>
</div>
""", unsafe_allow_html=True)

st.info(
    "REAL = OpenStreetMap data | ESTIMATED = calculated travel "
    "distance, time and cost. No live vehicle tracking is provided."
)

# --------------------------------------------------
# LOCATION DATA
# --------------------------------------------------

location_names = sorted(LOCATIONS.keys())


def get_coordinates(location):
    coordinates = LOCATIONS[location]
    return float(coordinates[0]), float(coordinates[1])


# --------------------------------------------------
# PUBLIC TRANSPORT DATA
# --------------------------------------------------

def load_osm_transport():
    import osmnx as ox

    tags = {
        "highway": "bus_stop",
        "amenity": "bus_station",
        "railway": ["station", "halt"]
    }

    place = "Varanasi, Uttar Pradesh, India"

    if hasattr(ox, "features_from_place"):
        data = ox.features_from_place(place, tags=tags)
    else:
        data = ox.geometries_from_place(place, tags=tags)

    records = []

    for _, row in data.iterrows():
        geometry = row.geometry

        if geometry is None or geometry.is_empty:
            continue

        point = geometry if geometry.geom_type == "Point" else geometry.centroid

        if row.get("railway") in ["station", "halt"]:
            transport_type = "Railway Station"
        elif row.get("amenity") == "bus_station":
            transport_type = "Bus Station"
        else:
            transport_type = "Bus Stop"

        records.append({
            "name": row.get("name") or "Unnamed transport point",
            "transport_type": transport_type,
            "latitude": point.y,
            "longitude": point.x,
            "source": "REAL - OpenStreetMap"
        })

    result = pd.DataFrame(records)

    if not result.empty:
        result = result.drop_duplicates(
            subset=["latitude", "longitude", "transport_type"]
        )

    return result


if "transport_data" not in st.session_state:
    if TRANSPORT_FILE.exists():
        st.session_state.transport_data = pd.read_csv(TRANSPORT_FILE)
    else:
        st.session_state.transport_data = pd.DataFrame(
            columns=[
                "name", "transport_type",
                "latitude", "longitude", "source"
            ]
        )

# --------------------------------------------------
# PUBLIC TRANSPORT OVERVIEW
# --------------------------------------------------

st.header("1. Public Transport Intelligence")

if st.button("🌐 Fetch REAL Transport Data from OpenStreetMap"):
    with st.spinner("Fetching Varanasi transport data..."):
        try:
            transport_df = load_osm_transport()

            if transport_df.empty:
                st.warning("No matching transport points were returned.")
            else:
                transport_df.to_csv(TRANSPORT_FILE, index=False)
                st.session_state.transport_data = transport_df
                st.success(
                    f"Successfully loaded {len(transport_df)} "
                    "transport points."
                )

        except Exception as error:
            st.error(
                "Could not fetch OSM data. Please try again later."
            )
            st.caption(f"Technical details: {error}")

transport_df = st.session_state.transport_data.copy()

if not transport_df.empty:

    c1, c2, c3 = st.columns(3)

    c1.metric("Total Transport Points", len(transport_df))
    c2.metric(
        "Bus Stops / Stations",
        transport_df["transport_type"].isin(
            ["Bus Stop", "Bus Station"]
        ).sum()
    )
    c3.metric(
        "Railway Points",
        (transport_df["transport_type"] == "Railway Station").sum()
    )

    selected_transport = st.multiselect(
        "Filter transport type",
        options=sorted(transport_df["transport_type"].unique()),
        default=sorted(transport_df["transport_type"].unique())
    )

    visible = transport_df[
        transport_df["transport_type"].isin(selected_transport)
    ]

    if not visible.empty:
        st.subheader("Public Transport Coverage Map")

        st.map(
            visible,
            latitude="latitude",
            longitude="longitude",
            size=12
        )

        st.dataframe(
            visible[
                ["name", "transport_type", "source"]
            ],
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("Select at least one transport type.")

else:
    st.warning(
        "Transport points are not loaded yet. "
        "Click the OpenStreetMap button above to fetch REAL data."
    )

# --------------------------------------------------
# PERSONAL TRANSPORT INTELLIGENCE
# --------------------------------------------------

st.divider()
st.header("2. Personal Transport Intelligence")

st.write(
    "Compare estimated travel time and cost for different "
    "personal transport modes."
)

r1, r2 = st.columns(2)

with r1:
    origin = st.selectbox(
        "Starting location",
        location_names,
        index=location_names.index("Sarnath")
        if "Sarnath" in location_names else 0
    )

with r2:
    destination_options = [
        name for name in location_names if name != origin
    ]

    destination = st.selectbox(
        "Destination",
        destination_options,
        index=destination_options.index("Assi Ghat")
        if "Assi Ghat" in destination_options else 0
    )

# --------------------------------------------------
# DISTANCE CALCULATION
# --------------------------------------------------

def haversine(lat1, lon1, lat2, lon2):
    earth_radius = 6371

    lat1, lat2 = math.radians(lat1), math.radians(lat2)
    dlat = lat2 - lat1
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    return 2 * earth_radius * math.asin(math.sqrt(a))


start_lat, start_lon = get_coordinates(origin)
end_lat, end_lon = get_coordinates(destination)

straight_distance = haversine(
    start_lat, start_lon, end_lat, end_lon
)

# Estimated road distance, not an actual routed distance
road_distance = straight_distance * 1.3

st.caption(
    "Distance is estimated using straight-line distance with a "
    "1.3 road-distance adjustment. It is not a live route calculation."
)

# --------------------------------------------------
# TRANSPORT COST ASSUMPTIONS
# --------------------------------------------------

st.subheader("Transport Cost Assumptions")

st.caption(
    "These are illustrative user-adjustable assumptions, "
    "not verified local fares or live market prices."
)

cost_inputs = {
    "Car": {"speed": 20, "rate": 12},
    "Bike": {"speed": 25, "rate": 3},
    "Auto Rickshaw": {"speed": 15, "rate": 18},
    "E-Rickshaw": {"speed": 12, "rate": 12}
}

cost_columns = st.columns(4)

for column, (mode, values) in zip(cost_columns, cost_inputs.items()):
    with column:
        values["rate"] = st.number_input(
            f"{mode} ₹/km",
            min_value=0.0,
            max_value=500.0,
            value=float(values["rate"]),
            step=1.0,
            key=f"rate_{mode}"
        )

# --------------------------------------------------
# COMPARISON CALCULATIONS
# --------------------------------------------------

comparison = []

for mode, values in cost_inputs.items():

    estimated_time = (
        road_distance / values["speed"]
    ) * 60

    estimated_cost = road_distance * values["rate"]

    comparison.append({
        "Transport Mode": mode,
        "Estimated Distance (km)": round(road_distance, 2),
        "Estimated Time (minutes)": round(estimated_time, 1),
        "Estimated Cost (₹)": round(estimated_cost, 2)
    })

comparison_df = pd.DataFrame(comparison)

# --------------------------------------------------
# RESULTS
# --------------------------------------------------

st.subheader("Transport Comparison Results")

m1, m2 = st.columns(2)

m1.metric(
    "Estimated Road Distance",
    f"{road_distance:.2f} km"
)

m2.metric(
    "Straight-line Distance",
    f"{straight_distance:.2f} km"
)

st.dataframe(
    comparison_df,
    use_container_width=True,
    hide_index=True
)

# --------------------------------------------------
# COST ANALYSIS
# --------------------------------------------------

# ========== PREMIUM TRANSPORT CHARTS ==========

chart_colors = ["#38BDF8", "#22D3EE", "#818CF8", "#34D399"]

st.markdown("## 📊 Transport Analytics")
st.caption("Compare estimated mobility cost and travel time across transport modes.")

# Cost chart
st.subheader("💰 Estimated Travel Cost")

fig = px.bar(
    comparison_df,
    x="Transport Mode",
    y="Estimated Cost (₹)",
    color="Transport Mode",
    color_discrete_sequence=chart_colors,
    text_auto=".2f"
)

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(10,25,45,0.5)",
    font=dict(color="#E2F3FF"),
    title=dict(text="Cost Comparison by Transport Mode", x=0.02),
    showlegend=False,
    margin=dict(l=20, r=20, t=65, b=20),
    xaxis_title="Transport Mode",
    yaxis_title="Estimated Cost (₹)"
)

fig.update_traces(
    marker_line_width=0,
    textposition="outside",
    hovertemplate="<b>%{x}</b><br>Estimated Cost: ₹%{y:.2f}<extra></extra>"
)

st.plotly_chart(fig, use_container_width=True)

# Travel time chart
st.subheader("⏱️ Estimated Travel Time")

time_fig = px.bar(
    comparison_df,
    x="Transport Mode",
    y="Estimated Time (minutes)",
    color="Transport Mode",
    color_discrete_sequence=chart_colors,
    text_auto=".1f"
)

time_fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(10,25,45,0.5)",
    font=dict(color="#E2F3FF"),
    title=dict(text="Travel Time Comparison", x=0.02),
    showlegend=False,
    margin=dict(l=20, r=20, t=65, b=20),
    xaxis_title="Transport Mode",
    yaxis_title="Estimated Time (minutes)"
)

time_fig.update_traces(
    marker_line_width=0,
    textposition="outside",
    hovertemplate="<b>%{x}</b><br>Estimated Time: %{y:.1f} minutes<extra></extra>"
)

st.plotly_chart(time_fig, use_container_width=True)

# --------------------------------------------------
# TIME ANALYSIS
# --------------------------------------------------

st.subheader("4. Estimated Travel Time Analysis")

time_fig = px.bar(
    comparison_df,
    x="Transport Mode",
    y="Estimated Time (minutes)",
    color="Transport Mode",
    title="Estimated Travel Time by Transport Mode",
    text_auto=".1f"
)

st.plotly_chart(time_fig, use_container_width=True)

# --------------------------------------------------
# RECOMMENDATION
# --------------------------------------------------

best_cost = comparison_df.loc[
    comparison_df["Estimated Cost (₹)"].idxmin()
]

best_time = comparison_df.loc[
    comparison_df["Estimated Time (minutes)"].idxmin()
]

st.subheader("5. Smart Transport Insights")

i1, i2 = st.columns(2)

i1.success(
    f"Lowest estimated cost: {best_cost['Transport Mode']} "
    f"(₹{best_cost['Estimated Cost (₹)']:.2f})"
)

i2.info(
    f"Shortest estimated time: {best_time['Transport Mode']} "
    f"({best_time['Estimated Time (minutes)']:.1f} minutes)"
)

st.caption(
    "All personal transport results are estimates based on "
    "assumed average speeds and cost per kilometre. "
    "They do not represent live traffic or official fares."
)

st.divider()

st.caption(
    "Varanasi Smart City Traffic & Route Intelligence Dashboard | "
    "Module 5 - Transport Intelligence"
)