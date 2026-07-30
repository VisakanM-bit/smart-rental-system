from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import select
from app.models import Alert, Machine, Rental, Telemetry
from app.presentation import hero, status_badge
from app.components.leaflet_tracker import render_live_tracker
from app.services.analytics import demand_forecast, detect_outliers, health_band

CHART_THEME = {"template": "plotly_dark", "paper_bgcolor": "rgba(0,0,0,0)", "plot_bgcolor": "rgba(0,0,0,0)", "font": {"color": "#d8e4f3"}, "margin": {"t": 46, "l": 12, "r": 12, "b": 12}}


def dataframe(session, model) -> pd.DataFrame:
    rows = session.scalars(select(model)).all()
    return pd.DataFrame([{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in rows])


def chart(figure) -> None:
    figure.update_layout(**CHART_THEME)
    st.plotly_chart(figure)


def page_intro(title: str, subtitle: str, eyebrow: str) -> None:
    hero(title, subtitle, eyebrow)


def dashboard(session) -> None:
    machines, rentals, telemetry, alerts = (dataframe(session, x) for x in (Machine, Rental, Telemetry, Alert))
    latest = telemetry.sort_values("timestamp").groupby("equipment_id").tail(1) if not telemetry.empty else telemetry
    active = rentals[rentals.contract_status.str.lower().eq("active")] if not rentals.empty else rentals
    page_intro("Fleet command center", "One focused view of availability, utilization, health, and the risks requiring action.", "Live rental intelligence")
    with st.container(border=True):
        st.image("assets/fleetsight-hero.png", caption="Connected equipment visibility — FleetSight original visual", width="stretch")

    with st.container(horizontal=True):
        st.metric("Fleet assets", len(machines), border=True)
        st.metric("On rent", len(active), border=True)
        st.metric("Available now", int(machines.current_status.str.lower().eq("available").sum()), border=True)
        st.metric("Open alerts", int((alerts.resolved == False).sum()) if not alerts.empty else 0, border=True)
        st.metric("Average health", f"{latest.condition_score.mean():.0f}%" if not latest.empty else "—", border=True)

    st.subheader("Operational view")
    layout = st.segmented_control("Dashboard focus", ["Executive", "Operations", "Risk"], default="Executive", label_visibility="collapsed")
    if layout == "Risk":
        _risk_block(alerts, latest, telemetry, machines)
        _fleet_block(machines, latest)
    elif layout == "Operations":
        _fleet_block(machines, latest)
        _risk_block(alerts, latest, telemetry, machines)
    else:
        _fleet_block(machines, latest)
        _risk_block(alerts, latest, telemetry, machines)

    with st.expander("Customize the command center", icon=":material/tune:"):
        st.caption("Choose the focus that moves the most relevant operational panels to the top. This keeps the dashboard compact on smaller screens without hiding data.")
        st.write("Executive balances fleet and risk. Operations prioritizes utilization. Risk puts open incidents first.")


def _fleet_block(machines: pd.DataFrame, latest: pd.DataFrame) -> None:
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.subheader("Fleet status")
        chart(px.pie(machines, names="current_status", hole=.68, color="current_status", color_discrete_sequence=["#5EEAD4", "#60A5FA", "#FBBF24", "#FB7185"]))
    with right, st.container(border=True):
        st.subheader("Health distribution")
        if not latest.empty:
            chart(px.histogram(latest, x="condition_score", nbins=12, color_discrete_sequence=["#5EEAD4"], labels={"condition_score": "Condition score"}))


def _risk_block(alerts: pd.DataFrame, latest: pd.DataFrame, telemetry: pd.DataFrame, machines: pd.DataFrame) -> None:
    left, right = st.columns([1.4, 1])
    with left, st.container(border=True):
        st.subheader("Assets needing attention")
        if alerts.empty:
            st.success("No unresolved alerts", icon=":material/check_circle:")
        else:
            queue = alerts[alerts.resolved == False].sort_values("created_at", ascending=False).head(8)
            st.dataframe(queue[["equipment_id", "category", "severity", "message", "created_at"]], hide_index=True, column_config={"severity": st.column_config.TextColumn("Severity"), "created_at": st.column_config.DatetimeColumn("Raised", format="MMM D, HH:mm")})
    with right, st.container(border=True):
        st.subheader("Live equipment tracking")
        if not latest.empty:
            severity = alerts[alerts.resolved == False].sort_values("created_at").groupby("equipment_id").tail(1)[["equipment_id", "severity"]] if not alerts.empty else pd.DataFrame(columns=["equipment_id", "severity"])
            assets = latest.merge(machines[["equipment_id", "equipment_type", "current_status", "geofence_status"]], on="equipment_id", how="left").merge(severity, on="equipment_id", how="left")
            render_live_tracker(assets, telemetry)


def assets(session) -> None:
    machines, telemetry = dataframe(session, Machine), dataframe(session, Telemetry)
    latest = telemetry.sort_values("timestamp").groupby("equipment_id").tail(1)[["equipment_id", "fuel_level_percent", "engine_temperature_c", "condition_score", "movement_status", "gps_lat", "gps_lon"]]
    view = machines.merge(latest, on="equipment_id", how="left")
    page_intro("Asset intelligence", "Find, inspect, and act on every machine from a single searchable fleet register.", "Asset visibility")
    filters, inspector = st.columns([1, 2])
    with filters, st.container(border=True):
        st.subheader("Find an asset")
        kinds = st.multiselect("Machine type", sorted(view.equipment_type.dropna().unique()))
        statuses = st.multiselect("Asset status", sorted(view.current_status.dropna().unique()))
        if kinds: view = view[view.equipment_type.isin(kinds)]
        if statuses: view = view[view.current_status.isin(statuses)]
        selected = st.selectbox("Open asset", view.equipment_id.tolist())
    with inspector, st.container(border=True):
        m = view[view.equipment_id == selected].iloc[0]
        st.subheader(f"{selected} · {m.brand} {m.model}")
        status_badge(m.current_status)
        a, b, c = st.columns(3)
        a.metric("Health", f"{m.condition_score:.0f}/100")
        b.metric("Fuel", f"{m.fuel_level_percent:.0f}%")
        c.metric("Temperature", f"{m.engine_temperature_c:.0f}°C")
        st.caption(f"{m.equipment_type} · {m.geofence_status.title()} geofence · {m.movement_status.title() if pd.notna(m.movement_status) else 'No movement signal'}")
    st.subheader("Fleet register")
    st.dataframe(view, hide_index=True, column_config={"condition_score": st.column_config.ProgressColumn("Health", min_value=0, max_value=100, format="%d"), "fuel_level_percent": st.column_config.ProgressColumn("Fuel", min_value=0, max_value=100, format="%d%%")})
    trend = telemetry[telemetry.equipment_id == selected].sort_values("timestamp")
    with st.container(border=True):
        st.subheader("Asset telemetry trend")
        chart(px.line(trend, x="timestamp", y=["fuel_level_percent", "engine_temperature_c", "condition_score"], labels={"value": "Reading", "variable": "Signal"}))


def rentals_page(session) -> None:
    rentals = dataframe(session, Rental)
    page_intro("Rental operations", "Track contracts, returns, assignment details, and commercial exposure without leaving fleet operations.", "Rental lifecycle")
    left, right = st.columns([1.55, 1])
    with left, st.container(border=True):
        st.subheader("Rental register")
        status = st.multiselect("Contract status", sorted(rentals.contract_status.dropna().unique()))
        view = rentals[rentals.contract_status.isin(status)] if status else rentals
        st.dataframe(view, hide_index=True, column_config={"total_rental_cost": st.column_config.NumberColumn("Rental value", format="₹%.0f"), "overdue_days": st.column_config.NumberColumn("Overdue days")})
    with right, st.container(border=True):
        st.subheader("Contract allocation")
        chart(px.bar(rentals.groupby("site_name").size().reset_index(name="contracts").sort_values("contracts"), x="contracts", y="site_name", orientation="h", color_discrete_sequence=["#60A5FA"]))


def alerts_page(session) -> None:
    alerts = dataframe(session, Alert)
    page_intro("Alert center", "A prioritized work queue for equipment risk, location exceptions, return exposure, and service needs.", "Action center")
    if alerts.empty:
        st.success("No alerts generated yet.", icon=":material/check_circle:")
        return
    left, right = st.columns([1, 1.4])
    with left, st.container(border=True):
        st.subheader("Alert mix")
        chart(px.histogram(alerts, x="category", color="severity", barmode="stack", color_discrete_map={"critical": "#fb7185", "warning": "#fbbf24"}))
    with right, st.container(border=True):
        st.subheader("Incident queue")
        severity = st.pills("Severity", sorted(alerts.severity.dropna().unique()), selection_mode="multi")
        view = alerts[alerts.severity.isin(severity)] if severity else alerts
        st.dataframe(view.sort_values("created_at", ascending=False), hide_index=True)


def forecasting_page(session) -> None:
    rentals, machines = dataframe(session, Rental), dataframe(session, Machine)
    rentals = rentals.merge(machines[["equipment_id", "equipment_type"]], on="equipment_id", how="left")
    page_intro("Demand planning", "Translate observed rental demand into site and equipment allocation decisions.", "Planning intelligence")
    try:
        from app.ml.pipeline import demand_predictions
        forecast = demand_predictions()
        st.caption("Showing the saved Holt-Winters seven-day forecast. Retrain it in ML models when data changes.")
        metric_label = "Next 7-day forecast"
        metric_value = f"{forecast.next_7_day_demand.sum():.0f}" if not forecast.empty else "—"
    except FileNotFoundError:
        forecast = demand_forecast(rentals)
        st.caption("Showing the capacity-buffer baseline. Train the ML model to replace it with a saved time-series forecast.")
        metric_label, metric_value = "Planned demand", f"{forecast.forecast_demand.sum():.0f}" if not forecast.empty else "—"
    st.metric(metric_label, metric_value, border=True)
    if not forecast.empty:
        y = "next_7_day_demand" if "next_7_day_demand" in forecast else "forecast_demand"
        left, right = st.columns([1.35, 1])
        with left, st.container(border=True):
            chart(px.bar(forecast.head(30), x="site_name", y=y, color="equipment_type", barmode="stack"))
        with right, st.container(border=True):
            st.subheader("Allocation list")
            st.dataframe(forecast, hide_index=True)


def maintenance_page(session) -> None:
    machines = dataframe(session, Machine)
    machines["next_service_due"] = pd.to_datetime(machines.last_service_date) + pd.to_timedelta(machines.service_interval_days, unit="D")
    page_intro("Maintenance readiness", "Make service timing visible before availability and rental commitments are affected.", "Uptime control")
    with st.container(border=True):
        st.subheader("Service calendar")
        st.dataframe(machines[["equipment_id", "equipment_type", "last_service_date", "next_service_due", "current_health_score"]].sort_values("next_service_due"), hide_index=True, column_config={"current_health_score": st.column_config.ProgressColumn("Health", min_value=0, max_value=100)})


def reports_page(session) -> None:
    machines, rentals, alerts = (dataframe(session, x) for x in (Machine, Rental, Alert))
    report = machines.groupby("equipment_type").agg(fleet_size=("equipment_id", "count"), average_health=("current_health_score", "mean")).reset_index()
    page_intro("Reports and exports", "Download fleet, rental, and alert evidence for operational reviews and stakeholder reporting.", "Reporting hub")
    with st.container(border=True):
        st.subheader("Fleet summary")
        st.dataframe(report, hide_index=True, column_config={"average_health": st.column_config.ProgressColumn("Average health", min_value=0, max_value=100)})
    with st.container(horizontal=True):
        st.download_button("Download fleet CSV", machines.to_csv(index=False).encode(), "fleet_report.csv", "text/csv", icon=":material/download:")
        st.download_button("Download rentals CSV", rentals.to_csv(index=False).encode(), "rental_report.csv", "text/csv", icon=":material/download:")
        st.download_button("Download alerts CSV", alerts.to_csv(index=False).encode(), "alerts_report.csv", "text/csv", icon=":material/download:")


def analytics_page(session) -> None:
    telemetry = dataframe(session, Telemetry)
    telemetry["is_anomaly"] = detect_outliers(telemetry)
    page_intro("Anomaly intelligence", "Separate normal operating variation from telemetry patterns that warrant a human review.", "AI monitoring")
    st.metric("ML-detected telemetry outliers", int(telemetry.is_anomaly.sum()), border=True)
    with st.container(border=True):
        chart(px.scatter(telemetry.sample(min(len(telemetry), 12000), random_state=42), x="engine_temperature_c", y="vibration_score", color="is_anomaly", hover_data=["equipment_id"], color_discrete_map={True: "#fb7185", False: "#60a5fa"}))


def ml_models_page(session) -> None:
    from app.data.importer import uploaded_data_available
    from app.ml.pipeline import demand_predictions, model_metrics, train_all
    metrics = model_metrics()
    page_intro("ML model studio", "Train, evaluate, and save the hybrid intelligence stack without disrupting fleet operations.", "Model operations")
    with st.container(border=True):
        source = st.segmented_control("Training data", ["synthetic", "uploaded"], default="uploaded" if uploaded_data_available() else "synthetic")
        if st.button("Train and save ML models", type="primary", icon=":material/model_training:"):
            with st.spinner("Engineering features, splitting data, fitting models, and saving artifacts..."):
                metrics = train_all(source)
            st.success(f"Training complete from {source} data. Models saved in data/models.", icon=":material/check_circle:")
    if not metrics:
        st.info("No saved models yet. Train synthetic models to begin the demo.", icon=":material/info:")
        return
    st.caption(f"Last trained: {metrics['trained_at']} · Source: {metrics['source']} · Rows: {metrics['training_rows']:,}")
    score_rows = [{"Model": model.replace("_", " ").title(), **metrics[model]} for model in ("maintenance_risk", "overdue_risk", "misuse_risk", "health_classification")]
    with st.container(border=True):
        st.subheader("Evaluation scorecard")
        st.dataframe(pd.DataFrame(score_rows), hide_index=True)
    try:
        forecast = demand_predictions().head(20)
        with st.container(border=True):
            st.subheader("Saved demand forecast")
            chart(px.bar(forecast, x="site_name", y="next_7_day_demand", color="equipment_type"))
    except FileNotFoundError:
        pass


def solutions_page(session) -> None:
    page_intro("Connected rental operations", "Purpose-built capability boxes make it easy to move from a business question to the right operational workspace.", "Platform modules")
    capabilities = [
        (":material/location_on:", "Live asset location", "GPS footprint, geofence status, movement signals, and equipment discovery.", "Assets"),
        (":material/timelapse:", "Utilization intelligence", "Engine hours, idle trends, working time, and capacity planning.", "Dashboard"),
        (":material/assignment_return:", "Rental lifecycle", "Contracts, due dates, customer assignments, and commercial exposure.", "Rental records"),
        (":material/health_and_safety:", "Machine health", "Condition scoring, fault signals, service timing, and health classifications.", "Maintenance"),
        (":material/notification_important:", "Proactive alerts", "A single incident queue for return, geofence, temperature, and maintenance risk.", "Alerts"),
        (":material/monitoring:", "Predictive models", "Anomalies, risk probabilities, and demand forecasting with a saved ML pipeline.", "ML models"),
        (":material/qr_code_scanner:", "Return-ready workflow", "A clear future-ready place for QR/barcode check-in and return evidence.", "Rental records"),
        (":material/receipt_long:", "Commercial reporting", "Fleet, rental, and alert exports for operations, finance, and reviews.", "Reports"),
    ]
    for row in range(0, len(capabilities), 2):
        cols = st.columns(2)
        for column, (icon, title, summary, destination) in zip(cols, capabilities[row:row + 2]):
            with column, st.container(border=True):
                st.subheader(f"{icon} {title}")
                st.write(summary)
                st.caption(f"Available in {destination}")


def integrity_ledger_page(session) -> None:
    from app.models import LedgerAccessEvent, LedgerBlock
    from app.services.ledger import append_snapshot, verify_chain, verify_current_snapshot

    page_intro("Integrity ledger", "Prove historical rental and telemetry batches were not silently changed, while keeping raw customer data off the ledger.", "Privacy-preserving blockchain pattern")
    chain = verify_chain(session)
    snapshot = verify_current_snapshot(session)
    with st.container(horizontal=True):
        st.metric("Chain status", "Verified" if chain["valid"] else "Compromised", border=True)
        st.metric("Blocks checked", chain["blocks_checked"], border=True)
        st.metric("Live snapshot", "Matches anchor" if snapshot["valid"] else "Changed since anchor", border=True)
        st.metric("Partitions checked", snapshot["partitions_checked"], border=True)
    st.caption("Only SHA-256 hashes, Merkle roots, tenant IDs, timestamps, and chain links are recorded. Raw GPS, telemetry, rental values, and personal data remain off-chain.")
    with st.container(border=True):
        st.subheader("Anchor current dataset")
        st.write("After an approved import or correction, create a new append-only snapshot. Historical blocks are never overwritten.")
        if st.button("Create integrity snapshot", type="primary", icon=":material/lock:"):
            result = append_snapshot(session, actor=st.session_state.user["name"])
            st.success(f"Created {result['blocks_added']} tenant/domain proofs in batch {result['batch_id']}.", icon=":material/verified:")
            st.rerun()
    left, right = st.columns([1.35, 1])
    with left, st.container(border=True):
        st.subheader("Latest cryptographic proofs")
        blocks = dataframe(session, LedgerBlock).sort_values("id", ascending=False).head(100)
        st.dataframe(blocks[["id", "tenant_id", "data_domain", "row_count", "merkle_root", "block_hash", "created_at"]], hide_index=True, column_config={"merkle_root": st.column_config.TextColumn("Merkle root", width="large"), "block_hash": st.column_config.TextColumn("Block hash", width="large"), "created_at": st.column_config.DatetimeColumn("Anchored", format="MMM D, YYYY HH:mm")})
    with right, st.container(border=True):
        st.subheader("Verification result")
        if chain["valid"] and snapshot["valid"]:
            st.success("The ledger and current dataset match their latest approved anchors.", icon=":material/verified_user:")
        else:
            st.warning("A mismatch is a review signal—not an automatic accusation. Check approved corrections, imports, and access logs before escalating.", icon=":material/warning:")
            st.json({"chain": chain, "snapshot": snapshot})
        events = dataframe(session, LedgerAccessEvent).sort_values("occurred_at", ascending=False).head(10)
        st.caption("Recent integrity events")
        st.dataframe(events[["actor", "tenant_id", "action", "resource", "occurred_at"]], hide_index=True)
