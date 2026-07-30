"""CSV importer for the supplied rental-data package.

The normalizers keep the public UI and agent code independent of source labels such
as `Inside`/`Outside`, `Yes`/`No`, and title-cased statuses.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd
from sqlalchemy import delete
from app.config import DATA_DIR
from app.models import Alert, Customer, Machine, Maintenance, Rental, Telemetry

UPLOAD_DIR = DATA_DIR / "uploaded"
MARKER = DATA_DIR / ".uploaded_dataset_loaded"
FILES = {"machines": "Machine_Master.csv", "rentals": "Rental_Transactions.csv", "telemetry": "Telemetry_Logs.csv", "maintenance": "Maintenance.csv", "customers": "Customer_Master.csv"}


def uploaded_data_available() -> bool:
    return all((UPLOAD_DIR / name).exists() for name in FILES.values())


def _records(frame: pd.DataFrame, dates: list[str], lower: list[str] = []) -> list[dict]:
    for name in dates:
        frame[name] = pd.to_datetime(frame[name], errors="coerce").dt.date
    for name in lower:
        frame[name] = frame[name].fillna("").astype(str).str.lower()
    frame = frame.where(pd.notna(frame), None)
    return frame.to_dict(orient="records")


def import_uploaded_dataset(session, force: bool = False) -> dict[str, int]:
    """Atomically replace demo records with the uploaded CSV package."""
    if not uploaded_data_available():
        raise FileNotFoundError(f"Expected CSV files in {UPLOAD_DIR}")
    if MARKER.exists() and not force:
        return {"status": 0}

    frames = {key: pd.read_csv(UPLOAD_DIR / filename) for key, filename in FILES.items()}
    customers = frames["customers"]
    customer_names = customers.set_index("customer_id")["customer_name"].to_dict()
    rentals = frames["rentals"]
    rentals["customer_name"] = rentals["customer_id"].map(customer_names).fillna("Unassigned customer")
    telemetry = frames["telemetry"]
    telemetry["geofence_flag"] = telemetry["geofence_flag"].astype(str).str.lower().eq("inside")
    telemetry["alert_flag"] = telemetry["alert_flag"].astype(str).str.lower().isin(["yes", "true", "1"])

    for model in (Alert, Telemetry, Maintenance, Rental, Customer, Machine):
        session.execute(delete(model))
    session.bulk_insert_mappings(Customer, _records(customers, []))
    session.bulk_insert_mappings(Machine, _records(frames["machines"], ["last_service_date"], ["current_status", "geofence_status", "demand_level"]))
    session.bulk_insert_mappings(Rental, _records(rentals, ["check_in_date", "expected_return_date", "actual_return_date"], ["payment_status", "contract_status"]))
    session.bulk_insert_mappings(Maintenance, _records(frames["maintenance"], ["service_date", "next_service_due_date"], ["service_status"]))
    # Timestamp is a DateTime column, unlike the date-only transactional fields.
    telemetry["timestamp"] = pd.to_datetime(telemetry["timestamp"], errors="coerce")
    telemetry = telemetry.where(pd.notna(telemetry), None)
    session.bulk_insert_mappings(Telemetry, telemetry.to_dict(orient="records"))
    session.commit()
    MARKER.touch()
    return {key: len(frame) for key, frame in frames.items()}
