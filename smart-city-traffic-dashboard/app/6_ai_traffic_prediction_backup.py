import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from src.traffic_predictor import train_model, predict_congestion
from src.traffic_simulator import AREAS, DAYS

st.set_page_config(
    page_title="AI Traffic Prediction | Varanasi Smart City",
    page_icon="🤖",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #07111f, #101d32);
    color: #e5edf7;
}
.block-container {
    padding-top: 1.5rem;
}
.hero {
    padding: 28px;
    border-radius: 18px;
    background: linear-gradient(110deg, #102b49, #164e63);
    border: 1px solid #25647a;
    margin-bottom: 22px;
}
.hero h1 { color: white; }
.hero p { color: #c5e8f3; }
.metric-card {
    background: #14243a;
    padding: 18px;
    border-radius: 14px;
    border: 1px solid #29445e;
}
.metric-value {
    font-size: 27px;
    font-weight: 700;
    color: #38d9e6;
}
.metric-label {
    color: #a9bfd3;
    font-size: 13px;
}
.section-title {
    color: #56d9e8;
    font-size: 22px;
    font-weight: 700;
    margin-top: 22px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <h1>🤖 AI Traffic Prediction & Smart Recommendations</h1>
    <p>Random Forest based congestion prediction for Varanasi localities</p>
</div>
""", unsafe_allow_html=True)

st.warning(
    "SIMULATED TRAINING DATA: The Random Forest model is trained "
    "on this project's simulated traffic dataset. Predictions are "
    "not live traffic measurements or verified real-world forecasts."
)

# ---------------- MODEL TRAINING ----------------

@st.cache_resource
def get_model_results():
    return train_model()

with st.spinner("Training Random Forest model..."):
    results = get_model_results()

model = results["model"]

st.success("Random Forest model trained successfully!")

# ---------------- MODEL PERFORMANCE ----------------

st.markdown(
    '<div class="section-title">📊 Model Performance</div>',
    unsafe_allow_html=True
)

m1, m2, m3, m4 = st.columns(4)

metrics = [
    ("MAE", f"{results['mae']:.2f}"),
    ("RMSE", f"{results['rmse']:.2f}"),
    ("R² Score", f"{results['r2']:.3f}"),
    ("Training Rows", str(results["training_rows"]))
]

for col, (label, value) in zip([m1, m2, m3, m4], metrics):
    with col:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-value">{value}</div>'
            f'<div class="metric-label">{label}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

st.caption(
    f"Test samples: {results['testing_rows']} | "
    "80% training / 20% testing split."
)

# ---------------- PREDICTION SETTINGS ----------------

st.markdown(
    '<div class="section-title">⚙️ Prediction Settings</div>',
    unsafe_allow_html=True
)

c1, c2, c3 = st.columns(3)

with c1:
    selected_area = st.selectbox("Select Locality", list(AREAS.keys()))

with c2:
    selected_day = st.selectbox("Select Day", DAYS)

with c3:
    selected_hour = st.slider(
        "Select Starting Hour",
        0, 23, 8,
        format="%d:00"
    )

# ---------------- SIX HOUR PREDICTION ----------------

forecast_rows = []

for step in range(6):
    absolute_hour = selected_hour + step
    day_offset = absolute_hour // 24
    hour = absolute_hour % 24
    day = DAYS[(DAYS.index(selected_day) + day_offset) % 7]

    predicted_value = predict_congestion(
        selected_area, day, hour, model
    )

    forecast_rows.append({
        "Day": day,
        "Hour": f"{hour:02d}:00",
        "Hour Number": hour,
        "Predicted Congestion": predicted_value
    })

forecast = pd.DataFrame(forecast_rows)

current_value = float(forecast.iloc[0]["Predicted Congestion"])

def risk_level(value):
    if value < 35:
        return "Low"
    elif value < 65:
        return "Moderate"
    return "High"

current_risk = risk_level(current_value)

# ---------------- PREDICTION KPIs ----------------

st.markdown(
    '<div class="section-title">🚦 Traffic Prediction Overview</div>',
    unsafe_allow_html=True
)

peak = forecast.loc[forecast["Predicted Congestion"].idxmax()]
best = forecast.loc[forecast["Predicted Congestion"].idxmin()]

k1, k2, k3 = st.columns(3)

with k1:
    st.metric("Predicted Congestion", f"{current_value:.1f}/100")

with k2:
    st.metric("Risk Level", current_risk)

with k3:
    st.metric("Peak Hour (Next 6 Hours)", peak["Hour"])

# ---------------- FORECAST CHART ----------------

st.markdown(
    '<div class="section-title">📈 Six-Hour ML Prediction</div>',
    unsafe_allow_html=True
)

fig = px.line(
    forecast,
    x="Hour",
    y="Predicted Congestion",
    markers=True,
    text="Predicted Congestion",
    title=f"Random Forest Prediction — {selected_area}"
)

fig.update_traces(
    line=dict(color="#38d9e6", width=3),
    marker=dict(size=9),
    textposition="top center"
)

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    yaxis=dict(range=[0, 100]),
    margin=dict(l=10, r=10, t=50, b=10)
)

st.plotly_chart(fig, use_container_width=True)

# ---------------- PEAK HOUR ANALYSIS ----------------

st.markdown(
    '<div class="section-title">⏰ City Peak-Hour Analysis</div>',
    unsafe_allow_html=True
)

city_predictions = []

for hour in range(24):
    values = [
        predict_congestion(area, selected_day, hour, model)
        for area in AREAS.keys()
    ]

    city_predictions.append({
        "Hour": hour,
        "Average Predicted Congestion": np.mean(values)
    })

city_df = pd.DataFrame(city_predictions)

peak_city = city_df.loc[
    city_df["Average Predicted Congestion"].idxmax()
]

fig_peak = px.bar(
    city_df,
    x="Hour",
    y="Average Predicted Congestion",
    title=f"Predicted City Congestion by Hour — {selected_day}"
)

fig_peak.update_traces(marker_color="#8b7cf6")

fig_peak.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    yaxis=dict(range=[0, 100]),
    xaxis=dict(tickmode="linear", dtick=1)
)

st.plotly_chart(fig_peak, use_container_width=True)

st.info(
    f"Highest predicted city congestion: "
    f"{int(peak_city['Hour']):02d}:00 "
    f"(index {peak_city['Average Predicted Congestion']:.1f})."
)

# ---------------- LOCALITY RISK ----------------

st.markdown(
    '<div class="section-title">📍 High-Risk Locality Identification</div>',
    unsafe_allow_html=True
)

locality_rows = []

for area in AREAS.keys():
    value = predict_congestion(
        area, selected_day, selected_hour, model
    )

    locality_rows.append({
        "Locality": area,
        "Predicted Congestion": value,
        "Risk Level": risk_level(value)
    })

locality_df = pd.DataFrame(locality_rows).sort_values(
    "Predicted Congestion",
    ascending=False
)

fig_risk = px.bar(
    locality_df,
    x="Predicted Congestion",
    y="Locality",
    color="Risk Level",
    orientation="h",
    title="Predicted Locality Congestion Risk",
    color_discrete_map={
        "Low": "#22c55e",
        "Moderate": "#f59e0b",
        "High": "#ef4444"
    }
)

fig_risk.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(range=[0, 100])
)

st.plotly_chart(fig_risk, use_container_width=True)

st.dataframe(
    locality_df,
    use_container_width=True,
    hide_index=True
)

# ---------------- SMART RECOMMENDATIONS ----------------

st.markdown(
    '<div class="section-title">💡 Smart Travel Recommendations</div>',
    unsafe_allow_html=True
)

if current_risk == "High":
    st.warning(
        f"High predicted congestion for {selected_area}. "
        f"The lowest predicted congestion in the next six hours "
        f"is around {best['Hour']}."
    )
elif current_risk == "Moderate":
    st.info(
        f"Moderate predicted congestion. If flexible, consider "
        f"travelling around {best['Hour']}."
    )
else:
    st.success(
        "The selected hour has comparatively low predicted congestion."
    )

st.write(
    f"**Lower predicted congestion locality:** "
    f"{locality_df.iloc[-1]['Locality']} "
    f"({locality_df.iloc[-1]['Predicted Congestion']:.1f}/100)"
)

st.caption(
    "These are model-based time and locality suggestions, not "
    "verified alternative road routes. Use Route Comparison "
    "for road-network route alternatives."
)

# ---------------- FEATURE IMPORTANCE ----------------

st.markdown(
    '<div class="section-title">🧠 Model Feature Importance</div>',
    unsafe_allow_html=True
)

importance = results["feature_importance"]

fig_importance = px.bar(
    importance,
    x="Importance",
    y="Feature",
    orientation="h",
    title="Random Forest Feature Importance"
)

fig_importance.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)"
)

st.plotly_chart(fig_importance, use_container_width=True)

# ---------------- DOWNLOAD ----------------

st.markdown(
    '<div class="section-title">📥 Download Prediction Report</div>',
    unsafe_allow_html=True
)

csv = forecast.to_csv(index=False).encode("utf-8")

st.download_button(
    "Download ML Prediction Report (CSV)",
    data=csv,
    file_name="varanasi_ml_traffic_predictions.csv",
    mime="text/csv"
)

st.caption(
    "Model: Random Forest Regressor | "
    "Data: Fixed-seed simulated traffic dataset | "
    "Predictions are experimental and not live traffic forecasts."
)