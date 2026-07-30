from __future__ import annotations

from datetime import date, datetime, timedelta
from sqlalchemy import select
from app.config import FUEL_DROP_THRESHOLD, IDLE_THRESHOLD, TEMP_THRESHOLD
from app.models import Alert, Machine, Rental, Telemetry


def _alert(session, equipment_id: str, category: str, severity: str, message: str) -> int:
    recent = datetime.utcnow() - timedelta(hours=12)
    duplicate = session.scalar(select(Alert).where(Alert.equipment_id == equipment_id, Alert.category == category, Alert.created_at >= recent, Alert.resolved.is_(False)))
    if duplicate:
        return 0
    session.add(Alert(equipment_id=equipment_id, category=category, severity=severity, message=message))
    return 1


def run_monitoring_agents(session) -> dict[str, int]:
    """Usage, condition, overdue, anomaly, and maintenance agents."""
    generated = {"usage": 0, "condition": 0, "overdue": 0, "anomaly": 0, "maintenance": 0}
    latest = session.execute(select(Telemetry).order_by(Telemetry.timestamp.desc())).scalars().all()
    seen: set[str] = set()
    for t in latest:
        if t.equipment_id in seen:
            continue
        seen.add(t.equipment_id)
        if t.engine_temperature_c > TEMP_THRESHOLD:
            generated["condition"] += _alert(session, t.equipment_id, "High temperature", "critical", f"Engine temperature is {t.engine_temperature_c:.1f}°C.")
        if t.idle_hours_today > IDLE_THRESHOLD:
            generated["usage"] += _alert(session, t.equipment_id, "Excessive idle", "warning", f"Idle time reached {t.idle_hours_today:.1f} hours today.")
        if not t.geofence_flag:
            generated["anomaly"] += _alert(session, t.equipment_id, "Geofence exit", "critical", "Machine is outside its assigned site geofence.")
        if t.fuel_consumed_liters > FUEL_DROP_THRESHOLD:
            generated["anomaly"] += _alert(session, t.equipment_id, "Fuel loss", "warning", f"Unusual fuel consumption: {t.fuel_consumed_liters:.1f} litres.")
    for rental in session.scalars(select(Rental).where(Rental.contract_status == "active")):
        days = max(0, (date.today() - rental.expected_return_date).days)
        rental.overdue_days = days
        if days:
            generated["overdue"] += _alert(session, rental.equipment_id, "Overdue rental", "critical", f"Return is overdue by {days} day(s).")
        elif rental.expected_return_date <= date.today() + timedelta(days=2):
            generated["overdue"] += _alert(session, rental.equipment_id, "Due soon", "warning", "Rental return is due within 48 hours.")
    for machine in session.scalars(select(Machine)):
        due = machine.last_service_date + timedelta(days=machine.service_interval_days)
        if due <= date.today() + timedelta(days=7):
            generated["maintenance"] += _alert(session, machine.equipment_id, "Maintenance due", "warning", f"Scheduled service due {due.isoformat()}.")
    session.commit()
    return generated
