from __future__ import annotations

import pandas as pd
from sklearn.ensemble import IsolationForest


def health_score(row: pd.Series) -> float:
    penalties = max(0, row.engine_temperature_c - 90) * 0.8 + row.idle_hours_today * 1.8
    penalties += max(0, row.vibration_score - 5) * 4 + (12 if row.fault_code else 0)
    penalties += (18 if not row.geofence_flag else 0)
    return round(max(0, min(100, 100 - penalties)), 1)


def health_band(score: float) -> str:
    return "Healthy" if score >= 80 else "Watch" if score >= 65 else "Warning" if score >= 45 else "Critical"


def detect_outliers(telemetry: pd.DataFrame) -> pd.Series:
    if len(telemetry) < 8:
        return pd.Series(False, index=telemetry.index)
    columns = ["engine_hours_today", "idle_hours_today", "fuel_consumed_liters", "engine_temperature_c", "vibration_score"]
    labels = IsolationForest(contamination=0.12, random_state=42).fit_predict(telemetry[columns].fillna(0))
    return pd.Series(labels == -1, index=telemetry.index)


def demand_forecast(rentals: pd.DataFrame) -> pd.DataFrame:
    active = rentals[rentals.contract_status == "active"].copy()
    if active.empty:
        return pd.DataFrame(columns=["site_name", "equipment_type", "active_rentals", "forecast_demand"])
    summary = active.groupby(["site_name", "equipment_type"]).size().reset_index(name="active_rentals")
    summary["forecast_demand"] = (summary.active_rentals * 1.18).round().astype(int).clip(lower=1)
    return summary.sort_values("forecast_demand", ascending=False)
