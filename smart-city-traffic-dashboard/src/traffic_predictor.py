import numpy as np
import pandas as pd
import joblib

from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.dummy import DummyRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder

from src.traffic_simulator import build_simulation, DAYS


MODEL_PATH = Path("models/traffic_random_forest.joblib")
ENCODER_PATH = Path("models/area_encoder.joblib")


def prepare_dataset():
    df = build_simulation().copy()

    area_encoder = LabelEncoder()
    df["area_encoded"] = area_encoder.fit_transform(df["area"])

    df["day_encoded"] = df["day"].map({
        day: index for index, day in enumerate(DAYS)
    })

    df["is_weekend"] = df["day"].isin(["Sat", "Sun"]).astype(int)

    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)

    # Chronological ordering
    df["time_key"] = df["day_encoded"] * 24 + df["hour"]
    df = df.sort_values(
        ["time_key", "area_encoded"]
    ).reset_index(drop=True)

    features = [
        "area_encoded",
        "day_encoded",
        "hour",
        "is_weekend",
        "hour_sin",
        "hour_cos"
    ]

    return df, area_encoder, features


def train_model():
    df, area_encoder, features = prepare_dataset()

    X = df[features]
    y = df["congestion_index"]

    # Split by time, keeping all localities at the same time together
    unique_times = np.sort(df["time_key"].unique())
    split_index = int(len(unique_times) * 0.80)
    cutoff = unique_times[split_index]

    train_mask = df["time_key"] < cutoff
    test_mask = df["time_key"] >= cutoff

    X_train = X.loc[train_mask]
    X_test = X.loc[test_mask]
    y_train = y.loc[train_mask]
    y_test = y.loc[test_mask]

    if X_train.empty or X_test.empty:
        raise ValueError("Not enough data for time-based evaluation.")

    # Random Forest model
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=12,
        min_samples_split=4,
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    # Simple baseline for comparison
    baseline = DummyRegressor(strategy="mean")
    baseline.fit(X_train, y_train)
    baseline_predictions = baseline.predict(X_test)

    # Evaluation metrics
    mae = mean_absolute_error(y_test, predictions)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    r2 = r2_score(y_test, predictions)

    baseline_mae = mean_absolute_error(
        y_test, baseline_predictions
    )
    baseline_rmse = np.sqrt(
        mean_squared_error(y_test, baseline_predictions)
    )
    baseline_r2 = r2_score(y_test, baseline_predictions)

    # Save trained model and locality encoder
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(area_encoder, ENCODER_PATH)

    test_results = df.loc[test_mask, [
        "area", "day", "hour", "congestion_index"
    ]].copy()

    test_results["Actual"] = y_test.values
    test_results["Random Forest Prediction"] = predictions
    test_results["Baseline Prediction"] = baseline_predictions

    feature_importance = pd.DataFrame({
        "Feature": features,
        "Importance": model.feature_importances_
    }).sort_values("Importance", ascending=False)

    return {
        "model": model,
        "mae": float(mae),
        "rmse": float(rmse),
        "r2": float(r2),
        "baseline_mae": float(baseline_mae),
        "baseline_rmse": float(baseline_rmse),
        "baseline_r2": float(baseline_r2),
        "training_rows": len(X_train),
        "testing_rows": len(X_test),
        "feature_importance": feature_importance,
        "test_results": test_results
    }


def predict_congestion(area, day, hour, model=None):
    if model is None:
        model = joblib.load(MODEL_PATH)

    area_encoder = joblib.load(ENCODER_PATH)

    if area not in area_encoder.classes_:
        raise ValueError(f"Unknown locality: {area}")

    area_encoded = int(area_encoder.transform([area])[0])
    day_encoded = DAYS.index(day)

    input_data = pd.DataFrame([{
        "area_encoded": area_encoded,
        "day_encoded": day_encoded,
        "hour": hour,
        "is_weekend": int(day in ["Sat", "Sun"]),
        "hour_sin": np.sin(2 * np.pi * hour / 24),
        "hour_cos": np.cos(2 * np.pi * hour / 24)
    }])

    prediction = model.predict(input_data)[0]

    return round(float(np.clip(prediction, 0, 100)), 1)