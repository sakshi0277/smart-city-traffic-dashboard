from pathlib import Path
from datetime import date, timedelta
import uuid

import pandas as pd
import plotly.express as px
import streamlit as st


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Road Closures | Varanasi Smart City",
    page_icon="🚧",
    layout="wide"
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "demo"
DATA_FILE = DATA_DIR / "road_closures.csv"

DATA_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# Varanasi DEMO LOCATION COORDINATES
# Approximate coordinates for demonstration only
# --------------------------------------------------

LOCATIONS = {
    "Godowlia": (25.3072, 83.0103),
    "Dashashwamedh Ghat": (25.3060, 83.0107),
    "Assi Ghat": (25.2880, 83.0067),
    "Lanka": (25.2820, 83.0060),
    "BHU Main Gate": (25.2677, 82.9890),
    "Sarnath": (25.3760, 83.0220),
    "Varanasi Cantt": (25.3330, 82.9870),
    "Sigra": (25.3100, 82.9870),
}


COLUMNS = [
    "report_id",
    "location",
    "latitude",
    "longitude",
    "alert_type",
    "severity",
    "status",
    "start_date",
    "expected_end",
    "affected_area",
    "description",
    "suggested_detour",
    "source"
]


# --------------------------------------------------
# SAMPLE DEMONSTRATION DATA
# Not official road closure information
# --------------------------------------------------

def create_demo_data():

    today = date.today()

    records = [
        {
            "report_id": "DEMO001",
            "location": "Godowlia",
            "latitude": 25.3072,
            "longitude": 83.0103,
            "alert_type": "Road Closure",
            "severity": "High",
            "status": "Active",
            "start_date": str(today),
            "expected_end": str(today + timedelta(days=2)),
            "affected_area": "Godowlia Market",
            "description": "Sample road closure for demonstration.",
            "suggested_detour": "Check Route Comparison for alternatives.",
            "source": "DEMO"
        },
        {
            "report_id": "DEMO002",
            "location": "Assi Ghat",
            "latitude": 25.2880,
            "longitude": 83.0067,
            "alert_type": "Construction",
            "severity": "Medium",
            "status": "Active",
            "start_date": str(today),
            "expected_end": str(today + timedelta(days=5)),
            "affected_area": "Assi Ghat Road",
            "description": "Sample construction activity.",
            "suggested_detour": "Use an alternate connecting road.",
            "source": "DEMO"
        },
        {
            "report_id": "DEMO003",
            "location": "Lanka",
            "latitude": 25.2820,
            "longitude": 83.0060,
            "alert_type": "Road Closure",
            "severity": "Medium",
            "status": "Planned",
            "start_date": str(today + timedelta(days=1)),
            "expected_end": str(today + timedelta(days=4)),
            "affected_area": "Lanka Crossing",
            "description": "Sample planned road maintenance.",
            "suggested_detour": "Check alternate routes before travel.",
            "source": "DEMO"
        },
        {
            "report_id": "DEMO004",
            "location": "Sarnath",
            "latitude": 25.3760,
            "longitude": 83.0220,
            "alert_type": "Construction",
            "severity": "Low",
            "status": "Active",
            "start_date": str(today),
            "expected_end": str(today + timedelta(days=7)),
            "affected_area": "Sarnath Approach Road",
            "description": "Sample road improvement work.",
            "suggested_detour": "Allow extra travel time.",
            "source": "DEMO"
        },
        {
            "report_id": "DEMO005",
            "location": "Sigra",
            "latitude": 25.3100,
            "longitude": 82.9870,
            "alert_type": "Road Closure",
            "severity": "High",
            "status": "Completed",
            "start_date": str(today - timedelta(days=4)),
            "expected_end": str(today - timedelta(days=1)),
            "affected_area": "Sigra Main Road",
            "description": "Sample completed roadwork record.",
            "suggested_detour": "Normal route can be checked.",
            "source": "DEMO"
        }
    ]

    return pd.DataFrame(records, columns=COLUMNS)


# --------------------------------------------------
# DATA LOADING AND SAVING
# --------------------------------------------------

def load_data():

    if not DATA_FILE.exists():
        df = create_demo_data()
        df.to_csv(DATA_FILE, index=False)
        return df

    try:
        df = pd.read_csv(DATA_FILE)

        if not set(COLUMNS).issubset(df.columns):
            st.warning("Data file format is incomplete. Recreating demo data.")
            df = create_demo_data()
            df.to_csv(DATA_FILE, index=False)

        return df

    except (OSError, pd.errors.ParserError, ValueError):
        st.error("Unable to read the road alerts data file.")
        return create_demo_data()


def save_data(df):
    df.to_csv(DATA_FILE, index=False)


df = load_data()


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.title("🚧 Road Closures & Construction Alerts")

st.markdown(
    "Monitor reported road closures, construction zones "
    "and potentially affected areas across Varanasi."
)

st.warning(
    "DATA NOTICE: This module currently uses DEMO sample records "
    "and USER-submitted reports. It is not connected to an official "
    "live road closure or municipal alert feed."
)

st.divider()


# --------------------------------------------------
# KPI CARDS
# --------------------------------------------------

active_df = df[df["status"] == "Active"]

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Alerts", len(df))

with col2:
    st.metric("Active Alerts", len(active_df))

with col3:
    st.metric(
        "Road Closures",
        len(df[df["alert_type"] == "Road Closure"])
    )

with col4:
    st.metric(
        "Construction Zones",
        len(df[df["alert_type"] == "Construction"])
    )

st.divider()


# --------------------------------------------------
# FILTERS
# --------------------------------------------------

st.subheader("🔎 Filter Road Alerts")

f1, f2, f3 = st.columns(3)

with f1:
    selected_location = st.selectbox(
        "Select locality",
        ["All"] + sorted(df["location"].dropna().unique().tolist())
    )

with f2:
    selected_type = st.selectbox(
        "Alert type",
    [
    "All",
    "Road Closure",
    "Construction",
    "Road Damage",
    "Waterlogging",
    "Accident",
    "Traffic Blockage"
]
    )

with f3:
    selected_status = st.selectbox(
        "Status",
        ["All", "Active", "Planned", "Completed",
         "Pending verification"]
    )

filtered_df = df.copy()

if selected_location != "All":
    filtered_df = filtered_df[
        filtered_df["location"] == selected_location
    ]

if selected_type != "All":
    filtered_df = filtered_df[
        filtered_df["alert_type"] == selected_type
    ]

if selected_status != "All":
    filtered_df = filtered_df[
        filtered_df["status"] == selected_status
    ]


# --------------------------------------------------
# INTERACTIVE MAP
# --------------------------------------------------

st.subheader("📍 Varanasi Road Alert Map")

st.caption(
    "Map markers show approximate locations of DEMO and USER reports. "
    "They do not confirm actual road conditions."
)

if not filtered_df.empty:

    map_df = filtered_df[
        ["latitude", "longitude", "location"]
    ].dropna()

    st.map(
        map_df.rename(
            columns={
                "latitude": "lat",
                "longitude": "lon"
            }
        ),
        zoom=11,
        use_container_width=True
    )

else:
    st.info("No alerts match the selected filters.")


# --------------------------------------------------
# ALERT TABLE
# --------------------------------------------------

st.subheader("📋 Road Alert Records")

display_columns = [
    "report_id",
    "location",
    "alert_type",
    "severity",
    "status",
    "affected_area",
    "expected_end",
    "source"
]

if not filtered_df.empty:

    st.dataframe(
        filtered_df[display_columns],
        use_container_width=True,
        hide_index=True
    )

else:
    st.info("No records to display.")


# --------------------------------------------------
# ALERT DETAILS
# --------------------------------------------------

st.subheader("🔍 Alert Details")

if not filtered_df.empty:

    selected_id = st.selectbox(
        "Choose an alert",
        filtered_df["report_id"].tolist()
    )

    selected_record = filtered_df[
        filtered_df["report_id"] == selected_id
    ].iloc[0]

    with st.container(border=True):

        st.markdown(
            f"### {selected_record['location']} "
            f"— {selected_record['alert_type']}"
        )

        st.write("**Report ID:**", selected_record["report_id"])
        st.write("**Severity:**", selected_record["severity"])
        st.write("**Status:**", selected_record["status"])
        st.write("**Affected area:**", selected_record["affected_area"])
        st.write("**Start date:**", selected_record["start_date"])
        st.write("**Expected end:**", selected_record["expected_end"])
        st.write("**Description:**", selected_record["description"])
        st.write("**Suggested detour:**", selected_record["suggested_detour"])
        st.write("**Data source:**", selected_record["source"])


# --------------------------------------------------
# ALERT ANALYTICS
# --------------------------------------------------

st.divider()
st.subheader("📊 Road Alert Analytics")

if not df.empty:

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:

        type_counts = (
            df.groupby("alert_type")
            .size()
            .reset_index(name="count")
        )

        fig1 = px.bar(
            type_counts,
            x="alert_type",
            y="count",
            color="alert_type",
            title="Alerts by Type",
            labels={
                "alert_type": "Alert Type",
                "count": "Number of Alerts"
            }
        )

        st.plotly_chart(fig1, use_container_width=True)

    with chart_col2:

        severity_counts = (
            df.groupby("severity")
            .size()
            .reset_index(name="count")
        )

        fig2 = px.pie(
            severity_counts,
            names="severity",
            values="count",
            hole=0.45,
            title="Alerts by Severity"
        )

        st.plotly_chart(fig2, use_container_width=True)


# --------------------------------------------------
# COMMUNITY REPORT FORM
# --------------------------------------------------

st.divider()
st.subheader("📝 Submit a Road Report")

st.caption(
    "Community reports are saved as USER submissions and remain "
    "unverified until independently checked."
)

with st.form("road_report_form", clear_on_submit=True):

    r1, r2 = st.columns(2)

    with r1:

        report_location = st.selectbox(
            "Locality",
            list(LOCATIONS.keys())
        )

    report_type = st.selectbox(
    "Report type",
    [
        "Road Closure",
        "Construction",
        "Road Damage",
        "Waterlogging",
        "Accident",
        "Traffic Blockage"
    ]
)
        )

        report_severity = st.selectbox(
            "Severity",
            ["Low", "Medium", "High"]
        )

        start_date = st.date_input(
            "Reported start date",
            value=date.today()
        )

    with r2:

        expected_end = st.date_input(
            "Expected end date",
            value=date.today() + timedelta(days=2)
        )

        affected_area = st.text_input(
            "Affected road / area",
            placeholder="Enter road or area name"
        )

        detour = st.text_input(
            "Suggested alternative",
            placeholder="Optional"
        )

    description = st.text_area(
        "Report description",
        placeholder="Describe the closure or construction activity..."
    )

    submitted = st.form_submit_button(
        "Submit Road Report",
        use_container_width=True
    )

    if submitted:

        if not affected_area.strip() or not description.strip():

            st.error(
                "Please enter the affected area and report description."
            )

        elif expected_end < start_date:

            st.error(
                "Expected end date cannot be before the start date."
            )

        else:

            lat, lon = LOCATIONS[report_location]

            new_record = {
                "report_id": "USER-" + uuid.uuid4().hex[:8].upper(),
                "location": report_location,
                "latitude": lat,
                "longitude": lon,
                "alert_type": report_type,
                "severity": report_severity,
                "status": "Pending verification",
                "start_date": str(start_date),
                "expected_end": str(expected_end),
                "affected_area": affected_area.strip(),
                "description": description.strip(),
                "suggested_detour": detour.strip() or "Not provided",
                "source": "USER"
            }

            updated_df = pd.concat(
                [df, pd.DataFrame([new_record])],
                ignore_index=True
            )

            save_data(updated_df)

            st.success(
                "Report submitted successfully! "
                "It is marked as Pending verification."
            )

            st.rerun()


# --------------------------------------------------
# DOWNLOAD REPORT
# --------------------------------------------------

st.divider()
st.subheader("📥 Export Road Alert Data")

csv_data = df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download Road Alerts CSV",
    data=csv_data,
    file_name="varanasi_road_alerts.csv",
    mime="text/csv",
    use_container_width=True
)

st.caption(
    "Varanasi Smart City Traffic & Route Intelligence Dashboard | "
    "Road Closures Module"
)