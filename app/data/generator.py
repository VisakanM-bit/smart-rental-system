from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from uuid import uuid4
from sqlalchemy import select
from app.models import Machine, Rental, Telemetry
from app.services.analytics import health_score

TYPES = ["Excavator", "Crane", "Bulldozer", "Grader", "Backhoe Loader"]
SITES = [("SITE-01", "Metro Line Extension", "Mumbai", 19.076, 72.878), ("SITE-02", "Harbor Logistics", "Chennai", 13.083, 80.271), ("SITE-03", "Greenfield Highway", "Pune", 18.520, 73.856)]


def seed_sample_data(session, machines_count: int = 24) -> None:
    if session.scalar(select(Machine.equipment_id).limit(1)):
        return
    random.seed(42)
    today = date.today()
    for i in range(1, machines_count + 1):
        equipment_id = f"EQ-{i:03d}"
        machine_type = TYPES[(i - 1) % len(TYPES)]
        status = random.choices(["rented", "available", "maintenance"], [0.58, 0.30, 0.12])[0]
        service = today - timedelta(days=random.randint(10, 190))
        machine = Machine(equipment_id=equipment_id, equipment_type=machine_type, brand=random.choice(["JCB", "Caterpillar", "Komatsu", "Volvo"]), model=f"{machine_type[:3].upper()}-{random.randint(200, 950)}", manufacture_year=random.randint(2016, 2024), machine_age_years=random.randint(1, 9), fuel_tank_capacity_liters=random.randint(140, 450), max_operating_hours_per_day=10, last_service_date=service, service_interval_days=180, current_status=status, current_health_score=80, current_location_lat=19.0 + random.random(), current_location_lon=72.5 + random.random(), geofence_status="inside", demand_level=random.choice(["low", "medium", "high"]))
        session.add(machine)
        rental_id = None
        if status == "rented":
            site_id, site_name, city, lat, lon = random.choice(SITES)
            expected = today + timedelta(days=random.randint(-5, 14))
            rental_id = f"RNT-{i:04d}"
            session.add(Rental(rental_id=rental_id, equipment_id=equipment_id, customer_id=f"CUS-{i % 7 + 1:03d}", customer_name=f"BuildRight {i % 7 + 1}", site_id=site_id, site_name=site_name, site_city=city, check_in_date=today - timedelta(days=random.randint(3, 25)), expected_return_date=expected, actual_return_date=None, rental_days=30, rental_rate_per_day=random.randint(8000, 23000), total_rental_cost=0, deposit_amount=50000, payment_status="paid", operator_id=f"OP-{i:03d}" if i % 6 else None, contract_status="active", overdue_days=max(0, (today - expected).days)))
        for hours_ago in range(0, 14 * 24, 6):
            temp = random.normalvariate(87, 8)
            idle = max(0, random.normalvariate(3, 1.8))
            fuel = max(5, min(98, 85 - hours_ago / 10 + random.uniform(-8, 8)))
            geofence = not (i % 11 == 0 and hours_ago == 0)
            row = type("R", (), {"engine_temperature_c": temp, "idle_hours_today": idle, "vibration_score": max(1, random.normalvariate(4.2, 1.5)), "fault_code": "E-201" if i % 13 == 0 else None, "geofence_flag": geofence})()
            session.add(Telemetry(telemetry_id=str(uuid4()), equipment_id=equipment_id, rental_id=rental_id, timestamp=datetime.now() - timedelta(hours=hours_ago), engine_hours_today=random.uniform(1, 11), total_engine_hours=random.randint(800, 13000), idle_hours_today=idle, fuel_level_percent=fuel, fuel_consumed_liters=random.uniform(3, 30), engine_temperature_c=temp, hydraulic_pressure_bar=random.uniform(120, 240), vibration_score=row.vibration_score, rpm=random.uniform(700, 2200), gps_lat=19 + random.random(), gps_lon=72 + random.random(), distance_from_site_km=0.8 if geofence else 14.5, geofence_flag=geofence, movement_status=random.choice(["moving", "idle", "working"]), fault_code=row.fault_code, alert_flag=False, alert_type=None, condition_score=health_score(row)))
    session.commit()
