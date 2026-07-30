"""Optional production bridge to a permissioned Hyperledger Fabric gateway."""
from __future__ import annotations

import json
from urllib.request import Request, urlopen
from app.config import FABRIC_API_TOKEN, FABRIC_GATEWAY_URL
from app.models import LedgerBlock


def fabric_ready() -> bool:
    return bool(FABRIC_GATEWAY_URL and FABRIC_API_TOKEN)


def anchor_proof(block: LedgerBlock) -> dict:
    """Submit non-sensitive proof metadata after explicit production setup."""
    if not fabric_ready():
        raise RuntimeError("Fabric gateway is not configured. Set FABRIC_GATEWAY_URL and FABRIC_API_TOKEN in deployment secrets.")
    payload = {"tenant_id": block.tenant_id, "data_domain": block.data_domain, "batch_id": block.batch_id, "row_count": block.row_count, "merkle_root": block.merkle_root, "previous_hash": block.previous_hash, "block_hash": block.block_hash, "created_at": block.created_at.isoformat()}
    request = Request(f"{FABRIC_GATEWAY_URL.rstrip('/')}/ledger/anchors", data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json", "Authorization": f"Bearer {FABRIC_API_TOKEN}"}, method="POST")
    with urlopen(request, timeout=10) as response:  # endpoint is deployment-controlled
        return json.loads(response.read().decode("utf-8"))
