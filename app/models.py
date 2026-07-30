from __future__ import annotations

from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="operator")
    display_name: Mapped[str] = mapped_column(String(100))


class Machine(Base):
    __tablename__ = "machines"
    equipment_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    equipment_type: Mapped[str] = mapped_column(String(50), index=True)
    brand: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(70))
    manufacture_year: Mapped[int] = mapped_column(Integer)
    machine_age_years: Mapped[float] = mapped_column(Float)
    fuel_tank_capacity_liters: Mapped[float] = mapped_column(Float)
    max_operating_hours_per_day: Mapped[float] = mapped_column(Float)
    last_service_date: Mapped[date] = mapped_column(Date)
    service_interval_days: Mapped[int] = mapped_column(Integer)
    current_status: Mapped[str] = mapped_column(String(30), index=True)
    current_health_score: Mapped[float] = mapped_column(Float)
    current_location_lat: Mapped[float] = mapped_column(Float)
    current_location_lon: Mapped[float] = mapped_column(Float)
    geofence_status: Mapped[str] = mapped_column(String(20))
    demand_level: Mapped[str] = mapped_column(String(20))


class Rental(Base):
    __tablename__ = "rentals"
    rental_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    equipment_id: Mapped[str] = mapped_column(ForeignKey("machines.equipment_id"), index=True)
    customer_id: Mapped[str] = mapped_column(String(30))
    customer_name: Mapped[str] = mapped_column(String(100))
    site_id: Mapped[str] = mapped_column(String(30))
    site_name: Mapped[str] = mapped_column(String(100))
    site_city: Mapped[str] = mapped_column(String(60))
    check_in_date: Mapped[date] = mapped_column(Date)
    expected_return_date: Mapped[date] = mapped_column(Date)
    actual_return_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    rental_days: Mapped[int] = mapped_column(Integer)
    rental_rate_per_day: Mapped[float] = mapped_column(Float)
    total_rental_cost: Mapped[float] = mapped_column(Float)
    deposit_amount: Mapped[float] = mapped_column(Float)
    payment_status: Mapped[str] = mapped_column(String(20))
    operator_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    contract_status: Mapped[str] = mapped_column(String(20), index=True)
    overdue_days: Mapped[int] = mapped_column(Integer, default=0)


class Telemetry(Base):
    __tablename__ = "telemetry"
    telemetry_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    equipment_id: Mapped[str] = mapped_column(ForeignKey("machines.equipment_id"), index=True)
    rental_id: Mapped[str | None] = mapped_column(ForeignKey("rentals.rental_id"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    engine_hours_today: Mapped[float] = mapped_column(Float)
    total_engine_hours: Mapped[float] = mapped_column(Float)
    idle_hours_today: Mapped[float] = mapped_column(Float)
    fuel_level_percent: Mapped[float] = mapped_column(Float)
    fuel_consumed_liters: Mapped[float] = mapped_column(Float)
    engine_temperature_c: Mapped[float] = mapped_column(Float)
    hydraulic_pressure_bar: Mapped[float] = mapped_column(Float)
    vibration_score: Mapped[float] = mapped_column(Float)
    rpm: Mapped[float] = mapped_column(Float)
    gps_lat: Mapped[float] = mapped_column(Float)
    gps_lon: Mapped[float] = mapped_column(Float)
    distance_from_site_km: Mapped[float] = mapped_column(Float)
    geofence_flag: Mapped[bool] = mapped_column(Boolean)
    movement_status: Mapped[str] = mapped_column(String(20))
    fault_code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    alert_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    condition_score: Mapped[float] = mapped_column(Float)


class Maintenance(Base):
    __tablename__ = "maintenance"
    maintenance_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    equipment_id: Mapped[str] = mapped_column(ForeignKey("machines.equipment_id"), index=True)
    service_date: Mapped[date] = mapped_column(Date)
    service_type: Mapped[str] = mapped_column(String(60))
    issue_reported: Mapped[str | None] = mapped_column(Text, nullable=True)
    part_replaced: Mapped[str | None] = mapped_column(String(120), nullable=True)
    downtime_hours: Mapped[float] = mapped_column(Float, default=0)
    service_cost: Mapped[float] = mapped_column(Float, default=0)
    next_service_due_date: Mapped[date] = mapped_column(Date)
    service_status: Mapped[str] = mapped_column(String(30))


class Customer(Base):
    __tablename__ = "customers"
    customer_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(100))
    contact_number: Mapped[str] = mapped_column(String(30))
    customer_type: Mapped[str] = mapped_column(String(50))
    city: Mapped[str] = mapped_column(String(60))
    total_rentals: Mapped[int] = mapped_column(Integer, default=0)
    total_amount_spent: Mapped[float] = mapped_column(Float, default=0)
    risk_level: Mapped[str] = mapped_column(String(20), default="low")
    late_return_count: Mapped[int] = mapped_column(Integer, default=0)


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(primary_key=True)
    equipment_id: Mapped[str] = mapped_column(String(30), index=True)
    category: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20), index=True)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)


class LedgerBlock(Base):
    """Hash-only append-only integrity proof; no customer data is stored here."""
    __tablename__ = "ledger_blocks"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(50), index=True)
    data_domain: Mapped[str] = mapped_column(String(40), index=True)
    batch_id: Mapped[str] = mapped_column(String(36), index=True)
    row_count: Mapped[int] = mapped_column(Integer)
    merkle_root: Mapped[str] = mapped_column(String(64))
    previous_hash: Mapped[str] = mapped_column(String(64))
    block_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class LedgerAccessEvent(Base):
    """Append-only access evidence for later compliance and misuse review."""
    __tablename__ = "ledger_access_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(80), index=True)
    tenant_id: Mapped[str] = mapped_column(String(50), index=True)
    action: Mapped[str] = mapped_column(String(60))
    resource: Mapped[str] = mapped_column(String(120))
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    event_hash: Mapped[str] = mapped_column(String(64), unique=True)
