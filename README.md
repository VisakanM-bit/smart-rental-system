# FleetSight — Smart Rental Intelligence

FleetSight is a hackathon-ready operational dashboard for heavy-equipment rental fleets. It turns rental records and IoT-style telemetry into an actionable view of fleet availability, machine condition, alerts, anomalies, demand, and service risk.

## Solution at a glance

- Unifies asset availability, rental operations, machine condition, maintenance, alerts and forecasting in one operational workspace.
- Uses AI-assisted decision support to detect unusual behaviour, predict maintenance, misuse and overdue-return risk, classify machine health, and forecast demand.
- Provides an interactive Leaflet map with colour-coded equipment status and recent movement history.
- Runs automated checks for high temperature, excessive idle time, unusual fuel consumption, geofence exits, overdue rentals and service due dates.
- Protects historical-record integrity with tenant-aware SHA-256 Merkle proofs and a hash chain, without putting sensitive GPS, financial or customer data on the ledger.
- Supports secure demo roles for administrators, managers, operators and customers, with reports available for export.

See [summary.txt](summary.txt) for the current project overview, achieved milestones and planned next steps.

The supplied dataset package has been imported into `data/uploaded/` and is used automatically at startup. See [DATA_INTERPRETATION_GUIDE.txt](C:\Users\pl\Desktop\visionaryminds\DATA_INTERPRETATION_GUIDE.txt) for reviewer-facing ranges, rules, expected results, and limitations.

## What is included

- Secure demo login with `admin`, `manager`, `operator`, and `customer` roles.
- Enterprise dashboard with fleet KPIs, status/condition charts, and rental allocation.
- Asset details with fuel, temperature, and health telemetry trends.
- Rental, alert, maintenance, forecasting, analytics, and downloadable report views.
- Five automated monitoring agents: usage, condition, overdue, demand-ready baseline, and anomaly/maintenance monitoring.
- SQLite prototype database; use the `DATABASE_URL` environment variable for PostgreSQL.
- Deterministic synthetic data that follows the supplied machine, rental, and telemetry schema.
- Hybrid ML pipeline with Isolation Forest, XGBoost, Holt-Winters forecasting, persisted artifacts, evaluation metrics, and dashboard training controls; see [ML_PIPELINE.md](C:\Users\pl\Desktop\visionaryminds\ML_PIPELINE.md).
- Tenant-aware, hash-only integrity ledger with Merkle proofs and an optional permissioned Hyperledger Fabric gateway integration; see [BLOCKCHAIN_SECURITY_ARCHITECTURE.md](C:\Users\pl\Desktop\visionaryminds\BLOCKCHAIN_SECURITY_ARCHITECTURE.md).

## Quick start in VS Code

1. Open this folder in VS Code and install the recommended extensions when prompted.
2. Create a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Copy `.env.example` to `.env`, then install packages and start the dashboard:

   ```powershell
   Copy-Item .env.example .env
   pip install -r requirements.txt
   streamlit run app.py
   ```

4. Open the local URL Streamlit prints (normally `http://localhost:8501`). Sign in with `admin` / `admin123`.

## Cloud database setup

For a managed PostgreSQL provider (Neon, Supabase, Railway, Azure, etc.), put its SQLAlchemy-compatible connection string in `.env`:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/fleetsight?sslmode=require
```

On the next run, FleetSight creates its tables automatically. Keep the URL and any FCM credential out of source control; `.env` is ignored.

## Project layout

```text
app.py                    Streamlit entry point and session/navigation shell
app/
  config.py               Environment-driven configuration
  database.py             Portable SQLAlchemy engine/session setup
  models.py               Relational data model
  data/generator.py       Repeatable synthetic machine/rental/telemetry data
  services/auth.py        Password hashing and authentication
  services/agents.py      Monitoring rules and alert lifecycle
  services/analytics.py   Health score, Isolation Forest, demand baseline
  ui.py                   Dashboard page renderers
data/                     Local SQLite database (generated at runtime)
.vscode/                  Recommended extensions and workspace paths
requirements.txt          Reproducible Python dependencies
REPORT.txt                Submission-oriented implementation report
```

## Extending it

The database layer accepts real data through the same tables and has no hard-coded absolute project paths. Add a data-import service that maps uploaded CSV headers to `Machine`, `Rental`, and `Telemetry`; dashboards and agents will immediately operate against the replacement records. For a production deployment, put the app behind SSO, manage schema migrations with Alembic, move agent runs to a scheduler/worker, and send alert payloads to FCM/email.
