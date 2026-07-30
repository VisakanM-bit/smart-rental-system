from __future__ import annotations

import numpy as np
import pandas as pd
from app.data.importer import FILES, UPLOAD_DIR, uploaded_data_available


def load_uploaded_frames() -> dict[str, pd.DataFrame]:
    if not uploaded_data_available():
        raise FileNotFoundError("Uploaded CSV package is unavailable in data/uploaded.")
    return {key: pd.read_csv(UPLOAD_DIR / filename) for key, filename in FILES.items()}


def synthetic_frames(seed: int = 42, telemetry_rows: int = 8000) -> dict[str, pd.DataFrame]:
    """Generate labelled-like fleet history for first model training/demo."""
    rng = np.random.default_rng(seed)
    n_machines, n_rentals = 120, 1600
    ids = np.array([f"SYN-{i:03d}" for i in range(n_machines)])
    dates = pd.Timestamp("2025-12-31") - pd.to_timedelta(rng.integers(0, 95, n_machines), unit="D")
    machines = pd.DataFrame({"equipment_id": ids, "equipment_type": rng.choice(["Excavator", "Crane", "Bulldozer", "Grader"], n_machines), "machine_age_years": rng.uniform(1, 11, n_machines), "max_operating_hours_per_day": rng.choice([8, 10, 12], n_machines), "last_service_date": dates, "service_interval_days": rng.choice([30, 45, 60], n_machines)})
    rental_ids = np.array([f"SR-{i:05d}" for i in range(n_rentals)])
    starts = pd.Timestamp("2025-01-01") + pd.to_timedelta(rng.integers(0, 360, n_rentals), unit="D")
    durations = rng.integers(2, 31, n_rentals)
    overdue = rng.choice([0, 0, 0, 0, 1, 2, 5, 8], n_rentals)
    rentals = pd.DataFrame({"rental_id": rental_ids, "equipment_id": rng.choice(ids, n_rentals), "site_name": rng.choice(["Metro Build", "Harbor Yard", "Airport Link", "North Highway"], n_rentals), "check_in_date": starts, "expected_return_date": starts + pd.to_timedelta(durations, unit="D"), "actual_return_date": starts + pd.to_timedelta(durations + overdue, unit="D"), "rental_days": durations, "rental_rate_per_day": rng.integers(12000, 30001, n_rentals), "total_rental_cost": durations * rng.integers(12000, 30001, n_rentals), "deposit_amount": rng.integers(24000, 60001, n_rentals), "overdue_days": overdue, "contract_status": np.where(overdue > 0, "Overdue", "Completed")})
    selected = rentals.iloc[rng.integers(0, n_rentals, telemetry_rows)].reset_index(drop=True)
    telemetry = pd.DataFrame({"telemetry_id": [f"ST-{i:06d}" for i in range(telemetry_rows)], "equipment_id": selected.equipment_id, "rental_id": selected.rental_id, "timestamp": pd.Timestamp("2025-01-01") + pd.to_timedelta(rng.integers(0, 365 * 24, telemetry_rows), unit="h"), "engine_hours_today": rng.uniform(0, 13, telemetry_rows), "total_engine_hours": rng.uniform(500, 15000, telemetry_rows), "idle_hours_today": rng.gamma(2, 1.5, telemetry_rows).clip(0, 12), "fuel_level_percent": rng.uniform(5, 100, telemetry_rows), "fuel_consumed_liters": rng.uniform(0, 240, telemetry_rows), "engine_temperature_c": rng.normal(91, 9, telemetry_rows).clip(65, 115), "hydraulic_pressure_bar": rng.uniform(180, 320, telemetry_rows), "vibration_score": rng.uniform(.5, 8, telemetry_rows), "rpm": rng.uniform(700, 2200, telemetry_rows), "distance_from_site_km": rng.uniform(0, 8, telemetry_rows), "geofence_flag": rng.choice(["Inside", "Outside"], telemetry_rows, p=[.93, .07]), "movement_status": rng.choice(["Working", "Idle", "Travelling", "Stopped"], telemetry_rows), "fault_code": rng.choice(["NONE", "TMP003", "VIB002"], telemetry_rows, p=[.89, .07, .04])})
    maintenance = pd.DataFrame({"maintenance_id": [], "equipment_id": [], "service_date": [], "next_service_due_date": []})
    return {"machines": machines, "rentals": rentals, "telemetry": telemetry, "maintenance": maintenance, "customers": pd.DataFrame()}


def load_frames(source: str = "synthetic") -> dict[str, pd.DataFrame]:
    return load_uploaded_frames() if source == "uploaded" else synthetic_frames()
