from __future__ import annotations

import streamlit as st
from app import ui
from app.data.generator import seed_sample_data
from app.data.importer import import_uploaded_dataset, uploaded_data_available
from app.database import get_session, init_database
from app.models import LedgerBlock, Machine
from app.presentation import apply_branding, hero
from app.services.agents import run_monitoring_agents
from app.services.auth import authenticate, seed_users
from app.services.ledger import append_snapshot

st.set_page_config(page_title="FleetSight | Smart rentals", page_icon=":material/precision_manufacturing:", layout="wide")
apply_branding()


@st.cache_resource
def setup() -> bool:
    init_database()
    with get_session() as session:
        seed_users(session)
        if uploaded_data_available():
            if session.get(Machine, "EQX1001") is None:
                import_uploaded_dataset(session, force=True)
        else:
            seed_sample_data(session)
        run_monitoring_agents(session)
        if session.get(LedgerBlock, 1) is None:
            append_snapshot(session)
    return True


setup()
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    _, login, _ = st.columns([1, 1.1, 1])
    with login:
        hero("FleetSight", "A clear operating system for connected rental equipment.", "Smart rental intelligence")
        with st.form("login", border=True):
            username = st.text_input("Username", value="admin", icon=":material/person:")
            password = st.text_input("Password", value="admin123", type="password", icon=":material/key:")
            if st.form_submit_button("Secure sign in", type="primary", icon=":material/login:"):
                with get_session() as session:
                    user = authenticate(session, username, password)
                if user:
                    st.session_state.user = {"name": user.display_name, "role": user.role}
                    st.rerun()
                else:
                    st.error("Invalid username or password", icon=":material/error:")
        st.caption("Demo: admin/admin123 · manager/manager123 · operator/operator123 · customer/customer123")
    st.stop()

with st.sidebar:
    st.title("FleetSight")
    st.caption("SMART RENTAL INTELLIGENCE")
    st.write(f"**{st.session_state.user['name']}**")
    st.caption(st.session_state.user["role"].title())
    page = st.radio("Workspace", ["Dashboard", "Connected operations", "Assets", "Rental records", "Alerts", "Forecasting", "Analytics", "ML models", "Maintenance", "Integrity ledger", "Reports", "Admin settings"])
    st.space("medium")
    if st.button("Run monitoring agents", icon=":material/play_circle:"):
        with get_session() as session:
            result = run_monitoring_agents(session)
        st.toast(f"Agents completed: {sum(result.values())} new alert(s)", icon=":material/check_circle:")
    if st.button("Logout", type="tertiary", icon=":material/logout:"):
        st.session_state.user = None
        st.rerun()

with get_session() as session:
    pages = {"Dashboard": ui.dashboard, "Connected operations": ui.solutions_page, "Assets": ui.assets, "Rental records": ui.rentals_page, "Alerts": ui.alerts_page, "Forecasting": ui.forecasting_page, "Analytics": ui.analytics_page, "ML models": ui.ml_models_page, "Maintenance": ui.maintenance_page, "Integrity ledger": ui.integrity_ledger_page, "Reports": ui.reports_page}
    pages.get(page, lambda s: st.info("Admin configuration is managed through `.env`; use DATABASE_URL to connect a cloud PostgreSQL instance.", icon=":material/settings:"))(session)
