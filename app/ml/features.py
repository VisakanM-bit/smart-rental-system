from __future__ import annotations

import numpy as np
import pandas as pd

NUMERIC_FEATURES = ["engine_hours_today", "total_engine_hours", "idle_hours_today", "fuel_level_percent", "fuel_consumed_liters", "engine_temperature_c", "hydraulic_pressure_bar", "vibration_score", "rpm", "distance_from_site_km", "machine_age_years", "max_operating_hours_per_day", "service_age_days", "service_interval_days", "overdue_days"]
CATEGORICAL_FEATURES = ["equipment_type", "movement_status", "geofence_status"]


def build_health_score(frame: pd.DataFrame) -> pd.DataFrame:
    """Explainable 0–100 score combining all requested fleet-risk signals."""
    data = frame.copy()
    penalty = (data.engine_hours_today - data.max_operating_hours_per_day).clip(lower=0) * 3
    penalty += (data.idle_hours_today - 3).clip(lower=0) * 2
    penalty += (25 - data.fuel_level_percent).clip(lower=0) * 0.45
    penalty += (data.engine_temperature_c - 90).clip(lower=0) * 0.9
    penalty += (data.vibration_score - 5).clip(lower=0) * 5
    penalty += (data.service_age_days - data.service_interval_days).clip(lower=0) * 0.18
    penalty += (~data.geofence_inside.astype(bool)).astype(int) * 18
    penalty += data.overdue_days.clip(lower=0) * 2.5
    data["rule_health_score"] = (100 - penalty).clip(0, 100).round(1)
    data["health_class"] = pd.cut(data.rule_health_score, bins=[-1, 44, 64, 79, 100], labels=["critical", "warning", "watch", "healthy"]).astype(str)
    return data


def engineer_features(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Join telemetry, machine, rental and service context into one model matrix."""
    machines, rentals, telemetry, maintenance = (frames[key].copy() for key in ("machines", "rentals", "telemetry", "maintenance"))
    telemetry["timestamp"] = pd.to_datetime(telemetry["timestamp"], errors="coerce")
    machines["last_service_date"] = pd.to_datetime(machines["last_service_date"], errors="coerce")
    machines["service_age_days"] = (telemetry.timestamp.max().normalize() - machines.last_service_date).dt.days.clip(lower=0).fillna(0)
    rentals["overdue_days"] = pd.to_numeric(rentals.overdue_days, errors="coerce").fillna(0)
    rental_cols = ["rental_id", "equipment_id", "overdue_days", "contract_status"]
    data = telemetry.merge(machines[["equipment_id", "equipment_type", "machine_age_years", "max_operating_hours_per_day", "service_age_days", "service_interval_days"]], on="equipment_id", how="left")
    data = data.merge(rentals[rental_cols], on=["rental_id", "equipment_id"], how="left")
    data["overdue_days"] = data.overdue_days.fillna(0)
    data["geofence_inside"] = data.geofence_flag.astype(str).str.lower().isin(["true", "1", "inside", "yes"])
    data["geofence_status"] = np.where(data.geofence_inside, "inside", "outside")
    data["movement_status"] = data.movement_status.fillna("unknown").astype(str).str.lower()
    data["equipment_type"] = data.equipment_type.fillna("unknown").astype(str)
    data["fault_present"] = ~data.fault_code.fillna("").astype(str).str.lower().isin(["", "none", "nan"])
    data = build_health_score(data)
    # Supervised labels use historical states/rules; replace with verified labels when available.
    data["maintenance_risk"] = ((data.service_age_days >= data.service_interval_days * .85) | (data.engine_temperature_c > 102) | data.fault_present).astype(int)
    data["overdue_risk"] = ((data.overdue_days > 0) | data.contract_status.fillna("").astype(str).str.lower().eq("overdue")).astype(int)
    data["misuse_risk"] = ((~data.geofence_inside) | (data.idle_hours_today > 5) | (data.engine_hours_today > data.max_operating_hours_per_day)).astype(int)
    for col in NUMERIC_FEATURES:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    return data
