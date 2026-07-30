from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from xgboost import XGBClassifier
from app.config import DATA_DIR
from app.ml.datasets import load_frames
from app.ml.features import CATEGORICAL_FEATURES, NUMERIC_FEATURES, engineer_features

MODEL_DIR = DATA_DIR / "models"
METRICS_PATH = MODEL_DIR / "metrics.json"
ANOMALY_COLUMNS = ["engine_hours_today", "idle_hours_today", "fuel_level_percent", "fuel_consumed_liters", "engine_temperature_c", "vibration_score", "distance_from_site_km", "overdue_days"]


def _preprocessor(numeric_features: list[str], categorical_features: list[str]) -> ColumnTransformer:
    return ColumnTransformer([("number", Pipeline([("impute", SimpleImputer(strategy="median"))]), numeric_features), ("category", Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical_features)])


def _xgb(multiclass: bool = False) -> XGBClassifier:
    return XGBClassifier(n_estimators=140, max_depth=5, learning_rate=.08, subsample=.85, colsample_bytree=.85, objective="multi:softprob" if multiclass else "binary:logistic", eval_metric="mlogloss" if multiclass else "logloss", n_jobs=2, random_state=42)


def _classification_metrics(y_true, predicted, probability=None) -> dict[str, float]:
    result = {"accuracy": round(float(accuracy_score(y_true, predicted)), 3), "precision": round(float(precision_score(y_true, predicted, average="weighted", zero_division=0)), 3), "recall": round(float(recall_score(y_true, predicted, average="weighted", zero_division=0)), 3), "f1": round(float(f1_score(y_true, predicted, average="weighted", zero_division=0)), 3)}
    if probability is not None and len(np.unique(y_true)) == 2:
        result["roc_auc"] = round(float(roc_auc_score(y_true, probability)), 3)
    return result


def _fit_classifier(data: pd.DataFrame, target: str, name: str, multiclass: bool = False) -> dict:
    feature_columns = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    # Current overdue days is an outcome, not a legitimate predictor of future
    # overdue risk; omit it from that model to prevent target leakage.
    if target == "overdue_risk":
        feature_columns = [column for column in feature_columns if column != "overdue_days"]
    X, y = data[feature_columns], data[target]
    labels = None
    if multiclass:
        labels = sorted(y.astype(str).unique().tolist())
        y = y.astype(str).map({label: index for index, label in enumerate(labels)})
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.2, random_state=42, stratify=y)
    model = Pipeline([("preprocess", _preprocessor([column for column in feature_columns if column in NUMERIC_FEATURES], CATEGORICAL_FEATURES)), ("model", _xgb(multiclass))])
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)
    probability = probabilities[:, 1] if not multiclass else None
    if labels is not None:
        model.health_labels = labels
    model.feature_columns = feature_columns
    joblib.dump(model, MODEL_DIR / f"{name}.joblib")
    return _classification_metrics(y_test, predictions, probability)


def _fit_anomaly_models(data: pd.DataFrame, rentals: pd.DataFrame) -> dict:
    telemetry_model = Pipeline([("impute", SimpleImputer(strategy="median")), ("model", IsolationForest(contamination=.12, n_estimators=180, random_state=42))])
    telemetry_model.fit(data[ANOMALY_COLUMNS])
    joblib.dump(telemetry_model, MODEL_DIR / "telemetry_anomaly.joblib")
    rental_features = rentals[["rental_days", "rental_rate_per_day", "total_rental_cost", "deposit_amount", "overdue_days"]].apply(pd.to_numeric, errors="coerce")
    rental_model = Pipeline([("impute", SimpleImputer(strategy="median")), ("model", IsolationForest(contamination=.10, n_estimators=180, random_state=42))])
    rental_model.fit(rental_features)
    joblib.dump(rental_model, MODEL_DIR / "rental_anomaly.joblib")
    return {"telemetry_training_rows": len(data), "rental_training_rows": len(rentals), "telemetry_contamination": .12, "rental_contamination": .10}


def _fit_demand_forecast(rentals: pd.DataFrame) -> dict:
    rentals = rentals.copy()
    rentals["check_in_date"] = pd.to_datetime(rentals.check_in_date, errors="coerce")
    rentals = rentals.dropna(subset=["check_in_date", "site_name", "equipment_id"])
    # Equipment type is joined by the caller before this model runs.
    models, summary = {}, []
    for (site, equipment_type), group in rentals.groupby(["site_name", "equipment_type"]):
        series = group.groupby("check_in_date").size().asfreq("D", fill_value=0).astype(float)
        key = f"{site}|||{equipment_type}"
        if len(series) >= 14 and series.sum() > 3:
            fitted = ExponentialSmoothing(series, trend="add", initialization_method="estimated").fit(optimized=True)
            forecast = float(max(0, fitted.forecast(7).sum()))
            models[key] = fitted
        else:
            forecast = float(series.tail(7).sum())
            models[key] = None
        summary.append({"site_name": site, "equipment_type": equipment_type, "next_7_day_demand": round(forecast, 1), "history_days": len(series)})
    bundle = {"models": models, "summary": summary, "trained_at": datetime.utcnow().isoformat()}
    joblib.dump(bundle, MODEL_DIR / "demand_forecast.joblib")
    return {"series": len(summary), "forecast_horizon_days": 7}


def train_all(source: str = "synthetic") -> dict:
    """Train all persisted models from synthetic or uploaded, schema-compatible data."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    frames = load_frames(source)
    data = engineer_features(frames)
    # Bound dashboard training time while retaining a reproducible representative set.
    train_data = data.sample(min(len(data), 30000), random_state=42)
    rentals = frames["rentals"].copy()
    machines = frames["machines"][["equipment_id", "equipment_type"]]
    rentals = rentals.merge(machines, on="equipment_id", how="left")
    metrics = {"source": source, "trained_at": datetime.utcnow().isoformat(), "training_rows": len(train_data), "maintenance_risk": _fit_classifier(train_data, "maintenance_risk", "maintenance_risk"), "overdue_risk": _fit_classifier(train_data, "overdue_risk", "overdue_risk"), "misuse_risk": _fit_classifier(train_data, "misuse_risk", "misuse_risk"), "health_classification": _fit_classifier(train_data, "health_class", "health_classification", multiclass=True), "anomaly_detection": _fit_anomaly_models(train_data, rentals), "demand_forecast": _fit_demand_forecast(rentals)}
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def model_metrics() -> dict | None:
    return json.loads(METRICS_PATH.read_text(encoding="utf-8")) if METRICS_PATH.exists() else None


def predict_risks(feature_frame: pd.DataFrame) -> pd.DataFrame:
    """Return probability and health predictions for already engineered feature rows."""
    if not (MODEL_DIR / "maintenance_risk.joblib").exists():
        raise FileNotFoundError("Models not trained. Run train_all first.")
    result = feature_frame.copy()
    for name in ("maintenance_risk", "overdue_risk", "misuse_risk"):
        model = joblib.load(MODEL_DIR / f"{name}.joblib")
        result[f"{name}_probability"] = model.predict_proba(result[model.feature_columns])[:, 1].round(3)
    health = joblib.load(MODEL_DIR / "health_classification.joblib")
    encoded = health.predict(result[health.feature_columns]).astype(int)
    result["predicted_health_class"] = [health.health_labels[value] for value in encoded]
    return result


def detect_anomalies(feature_frame: pd.DataFrame, rental_frame: pd.DataFrame | None = None) -> pd.DataFrame:
    result = feature_frame.copy()
    model = joblib.load(MODEL_DIR / "telemetry_anomaly.joblib")
    result["telemetry_anomaly"] = model.predict(result[ANOMALY_COLUMNS]) == -1
    if rental_frame is not None:
        rental_model = joblib.load(MODEL_DIR / "rental_anomaly.joblib")
        cols = ["rental_days", "rental_rate_per_day", "total_rental_cost", "deposit_amount", "overdue_days"]
        rental_frame = rental_frame.copy()
        rental_frame["rental_anomaly"] = rental_model.predict(rental_frame[cols].apply(pd.to_numeric, errors="coerce")) == -1
    return result


def demand_predictions() -> pd.DataFrame:
    bundle = joblib.load(MODEL_DIR / "demand_forecast.joblib")
    return pd.DataFrame(bundle["summary"]).sort_values("next_7_day_demand", ascending=False)
