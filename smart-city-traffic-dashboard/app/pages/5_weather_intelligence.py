from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st


# ========== PAGE CONFIGURATION ==========

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #07111f, #10233d, #091827);
    color: #eaf4ff;
}

header[data-testid="stHeader"] {
    background: transparent;
}

.weather-hero {
    padding: 32px;
    border-radius: 20px;
    background: linear-gradient(115deg, #12365d, #075985, #0891b2);
    border: 1px solid rgba(125, 211, 252, 0.3);
    box-shadow: 0 12px 35px rgba(0, 160, 255, 0.16);
    animation: fadeIn 1s ease;
    margin-bottom: 25px;
}

.weather-title {
    font-size: 32px;
    font-weight: 800;
    color: white;
}

.weather-subtitle {
    color: #d5f1ff;
    margin-top: 8px;
    font-size: 15px;
}

div[data-testid="stMetric"] {
    background: rgba(20, 47, 75, 0.8);
    border: 1px solid rgba(69, 190, 255, 0.25);
    padding: 20px;
    border-radius: 16px;
    transition: 0.3s ease;
    animation: fadeIn 0.8s ease;
}

div[data-testid="stMetric"]:hover {
    transform: translateY(-5px);
    border-color: #38bdf8;
    box-shadow: 0 8px 25px rgba(56, 189, 248, 0.2);
}

div[data-testid="stMetricValue"] {
    color: #38d9ff;
    font-weight: 800;
}

.stButton > button {
    background: linear-gradient(90deg, #087eae, #06b6d4);
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 700;
    transition: 0.3s ease;
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 20px rgba(6, 182, 212, 0.35);
    color: white;
}

h1, h2, h3 {
    color: #e5f5ff !important;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(15px); }
    to { opacity: 1; transform: translateY(0); }
}

hr {
    border-color: rgba(56, 189, 248, 0.2);
}
</style>
""", unsafe_allow_html=True)


# ========== VARANASI LOCATION ==========

LATITUDE = 25.3176
LONGITUDE = 82.9739

API_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES = {
    0: "Clear Sky",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing Rime Fog",
    51: "Light Drizzle",
    53: "Moderate Drizzle",
    55: "Dense Drizzle",
    61: "Slight Rain",
    63: "Moderate Rain",
    65: "Heavy Rain",
    71: "Slight Snow",
    73: "Moderate Snow",
    75: "Heavy Snow",
    80: "Rain Showers",
    81: "Moderate Rain Showers",
    82: "Violent Rain Showers",
    95: "Thunderstorm",
    96: "Thunderstorm with Hail",
    99: "Heavy Thunderstorm"
}


# ========== API DATA FETCHING ==========

@st.cache_data(ttl=1800)
def fetch_weather():

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": (
            "temperature_2m,relative_humidity_2m,"
            "apparent_temperature,precipitation,"
            "weather_code,wind_speed_10m"
        ),
        "hourly": (
            "temperature_2m,relative_humidity_2m,"
            "precipitation_probability,precipitation,"
            "wind_speed_10m,weather_code"
        ),
        "forecast_days": 1,
        "timezone": "Asia/Kolkata"
    }

    response = requests.get(API_URL, params=params, timeout=25)
    response.raise_for_status()

    return response.json()


# ========== HERO SECTION ==========

st.markdown("""
<div class="weather-hero">
    <div class="weather-title">
        🌦️ WEATHER & ROAD INTELLIGENCE
    </div>
    <div class="weather-subtitle">
        VARANASI SMART CITY | LIVE WEATHER MONITORING
    </div>
    <div class="weather-subtitle">
        Monitor atmospheric conditions and understand
        their possible impact on urban mobility.
    </div>
</div>
""", unsafe_allow_html=True)

st.info(
    "REAL DATA: Open-Meteo weather API | "
    "TRAVEL IMPACT: Rule-based estimates, not official warnings."
)

# ========== FETCH BUTTON ==========

if st.button("🌐 Fetch Latest Weather Data"):

    st.cache_data.clear()

    with st.spinner("Connecting to Open-Meteo..."):

        try:
            st.session_state.weather_data = fetch_weather()
            st.success("Weather data successfully updated!")

        except Exception as error:
            st.error("Unable to fetch weather data. Please try again.")
            st.caption(f"Technical details: {error}")


# ========== DISPLAY WEATHER ==========

if "weather_data" not in st.session_state:

    with st.spinner("Loading Varanasi weather..."):

        try:
            st.session_state.weather_data = fetch_weather()

        except Exception as error:
            st.error("Weather service is temporarily unavailable.")
            st.caption(f"Technical details: {error}")
            st.stop()


weather = st.session_state.weather_data
current = weather["current"]
hourly = weather["hourly"]

temperature = current["temperature_2m"]
feels_like = current["apparent_temperature"]
humidity = current["relative_humidity_2m"]
wind = current["wind_speed_10m"]
rain = current["precipitation"]

weather_code = current["weather_code"]
condition = WEATHER_CODES.get(weather_code, "Unknown Condition")

weather_time = current["time"]

# ========== CURRENT WEATHER ==========

st.header("🌤️ Current Weather Conditions")

st.caption(
    f"📍 Varanasi, Uttar Pradesh | "
    f"Last reported: {weather_time}"
)

c1, c2, c3, c4 = st.columns(4)

c1.metric("🌡️ Temperature", f"{temperature} °C")
c2.metric("💧 Humidity", f"{humidity}%")
c3.metric("💨 Wind Speed", f"{wind} km/h")
c4.metric("🌧️ Precipitation", f"{rain} mm")

m1, m2 = st.columns(2)

m1.metric("Feels Like", f"{feels_like} °C")
m2.metric("Weather Condition", condition)

st.divider()

# ========== HOURLY DATA ==========

st.header("📈 Hourly Weather Analytics")

weather_df = pd.DataFrame({
    "Time": pd.to_datetime(hourly["time"]),
    "Temperature": hourly["temperature_2m"],
    "Humidity": hourly["relative_humidity_2m"],
    "Rain Probability": hourly["precipitation_probability"],
    "Rainfall": hourly["precipitation"],
    "Wind Speed": hourly["wind_speed_10m"]
})

# Use upcoming hours for analysis
current_hour = pd.to_datetime(weather_time).floor("h")

upcoming = weather_df[
    weather_df["Time"] >= current_hour
].copy()

if upcoming.empty:
    upcoming = weather_df.copy()

# Temperature chart
st.subheader("🌡️ Temperature Forecast")

temp_fig = px.line(
    upcoming,
    x="Time",
    y="Temperature",
    markers=True,
    title="Hourly Temperature Forecast",
    color_discrete_sequence=["#38BDF8"]
)

temp_fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(10,25,45,0.5)",
    font=dict(color="#E2F3FF"),
    margin=dict(l=20, r=20, t=60, b=20)
)

st.plotly_chart(temp_fig, use_container_width=True)

# Rainfall chart
st.subheader("🌧️ Rainfall & Precipitation Probability")

rain_fig = px.bar(
    upcoming,
    x="Time",
    y="Rain Probability",
    title="Hourly Rain Probability",
    color="Rain Probability",
    color_continuous_scale=["#164e63", "#06b6d4", "#38bdf8"]
)

rain_fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(10,25,45,0.5)",
    font=dict(color="#E2F3FF"),
    coloraxis_showscale=False,
    margin=dict(l=20, r=20, t=60, b=20)
)

st.plotly_chart(rain_fig, use_container_width=True)

# Wind chart
st.subheader("💨 Wind Speed Monitoring")

wind_fig = px.area(
    upcoming,
    x="Time",
    y="Wind Speed",
    title="Hourly Wind Speed",
    color_discrete_sequence=["#818CF8"]
)

wind_fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(10,25,45,0.5)",
    font=dict(color="#E2F3FF"),
    margin=dict(l=20, r=20, t=60, b=20)
)

st.plotly_chart(wind_fig, use_container_width=True)

st.divider()

# ========== WEATHER BASED TRAVEL INSIGHTS ==========

st.header("🚦 Weather-Based Travel Intelligence")

alerts = []

max_rain_probability = upcoming["Rain Probability"].max()
max_wind = upcoming["Wind Speed"].max()
max_temperature = upcoming["Temperature"].max()

if max_rain_probability >= 70:
    alerts.append(
        ("🌧️ High Rain Probability",
         "Rain may affect visibility and road conditions. "
         "Allow extra travel time.")
    )

if max_wind >= 35:
    alerts.append(
        ("💨 Strong Wind Conditions",
         "Strong winds may affect two-wheeler travel. "
         "Ride carefully.")
    )

if max_temperature >= 40:
    alerts.append(
        ("🔥 High Temperature",
         "High temperatures may increase travel discomfort. "
         "Stay hydrated.")
    )

if weather_code in [45, 48]:
    alerts.append(
        ("🌫️ Fog Conditions",
         "Fog may reduce visibility. Drive carefully.")
    )

if weather_code in [65, 82, 95, 96, 99]:
    alerts.append(
        ("⚠️ Severe Weather Indicator",
         "Current weather conditions may require additional "
         "travel caution.")
    )

if alerts:

    for title, message in alerts:
        st.warning(f"**{title}** — {message}")

else:
    st.success(
        "No major weather-based travel indicators "
        "were detected by the current rule set."
    )

st.caption(
    "These are automated informational indicators based on "
    "weather thresholds. They are not official weather alerts "
    "or verified road-condition reports."
)

# ========== SUMMARY ==========

st.header("📋 Weather Summary")

summary = pd.DataFrame({
    "Parameter": [
        "Temperature",
        "Feels Like",
        "Humidity",
        "Wind Speed",
        "Precipitation",
        "Weather Condition"
    ],
    "Current Value": [
        f"{temperature} °C",
        f"{feels_like} °C",
        f"{humidity}%",
        f"{wind} km/h",
        f"{rain} mm",
        condition
    ],
    "Source": ["REAL - Open-Meteo"] * 6
})

st.dataframe(
    summary,
    use_container_width=True,
    hide_index=True
)

st.download_button(
    "⬇️ Download Weather Report",
    data=summary.to_csv(index=False),
    file_name="varanasi_weather_report.csv",
    mime="text/csv"
)

st.divider()

st.caption(
    "VARANASI SMART CITY | MODULE 06 - WEATHER & "
    "ROAD CONDITION INTELLIGENCE"
)