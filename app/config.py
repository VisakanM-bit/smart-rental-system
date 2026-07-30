from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'rental_intelligence.db'}")
TEMP_THRESHOLD = float(os.getenv("ALERT_TEMPERATURE_C", "105"))
IDLE_THRESHOLD = float(os.getenv("ALERT_IDLE_HOURS", "5"))
FUEL_DROP_THRESHOLD = float(os.getenv("ALERT_FUEL_DROP_PERCENT", "20"))
LEDGER_MODE = os.getenv("LEDGER_MODE", "hash-chain")
FABRIC_GATEWAY_URL = os.getenv("FABRIC_GATEWAY_URL", "")
FABRIC_API_TOKEN = os.getenv("FABRIC_API_TOKEN", "")
ROLES = ("admin", "manager", "operator", "customer")
