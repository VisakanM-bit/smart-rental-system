"""Privacy-preserving, tamper-evident historical-data ledger.

This is a local permissioned ledger for the prototype. It records only hashes,
not raw customer, GPS, financial, or telemetry data. A Fabric adapter can submit
the same `block_hash`/`merkle_root` to a consortium network in production.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime
from uuid import uuid4
from sqlalchemy import select
from app.models import Customer, LedgerAccessEvent, LedgerBlock, Machine, Maintenance, Rental, Telemetry

FLEET_OWNER = "FLEET_OWNER"


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def merkle_root(records: list[dict]) -> str:
    """Deterministic root; any row/value alteration changes the committed proof."""
    hashes = [canonical_hash(record) for record in sorted(records, key=lambda item: canonical_hash(item))]
    if not hashes:
        return canonical_hash({"empty": True})
    while len(hashes) > 1:
        if len(hashes) % 2:
            hashes.append(hashes[-1])
        hashes = [canonical_hash({"left": hashes[index], "right": hashes[index + 1]}) for index in range(0, len(hashes), 2)]
    return hashes[0]


def _records(session, model) -> list[dict]:
    return [{column.name: getattr(row, column.name) for column in row.__table__.columns} for row in session.scalars(select(model)).all()]


def _tenant_partitions(session) -> dict[tuple[str, str], list[dict]]:
    rentals = _records(session, Rental)
    rental_tenants = {row["rental_id"]: row["customer_id"] for row in rentals}
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for rental in rentals:
        groups[(rental["customer_id"], "rental")].append(rental)
    for telemetry in _records(session, Telemetry):
        groups[(rental_tenants.get(telemetry.get("rental_id"), FLEET_OWNER), "telemetry")].append(telemetry)
    for customer in _records(session, Customer):
        groups[(customer["customer_id"], "customer")].append(customer)
    for machine in _records(session, Machine):
        groups[(FLEET_OWNER, "machine")].append(machine)
    for maintenance in _records(session, Maintenance):
        groups[(FLEET_OWNER, "maintenance")].append(maintenance)
    return groups


def append_snapshot(session, actor: str = "system-import") -> dict[str, int]:
    """Commit current DB state as hash-only tenant/domain batch proofs."""
    batch_id = str(uuid4())
    added = 0
    for (tenant_id, domain), records in _tenant_partitions(session).items():
        previous = session.scalar(select(LedgerBlock).where(LedgerBlock.tenant_id == tenant_id, LedgerBlock.data_domain == domain).order_by(LedgerBlock.id.desc()))
        root = merkle_root(records)
        previous_hash = previous.block_hash if previous else "0" * 64
        created_at = datetime.utcnow()
        block_hash = canonical_hash({"tenant_id": tenant_id, "domain": domain, "batch_id": batch_id, "row_count": len(records), "merkle_root": root, "previous_hash": previous_hash, "created_at": created_at.isoformat()})
        session.add(LedgerBlock(tenant_id=tenant_id, data_domain=domain, batch_id=batch_id, row_count=len(records), merkle_root=root, previous_hash=previous_hash, block_hash=block_hash, created_at=created_at))
        added += 1
    log_access(session, actor, FLEET_OWNER, "snapshot_anchored", f"batch:{batch_id}")
    session.commit()
    return {"blocks_added": added, "batch_id": batch_id}


def verify_chain(session) -> dict[str, object]:
    blocks = session.scalars(select(LedgerBlock).order_by(LedgerBlock.id)).all()
    expected: dict[tuple[str, str], str] = defaultdict(lambda: "0" * 64)
    invalid: list[int] = []
    for block in blocks:
        key = (block.tenant_id, block.data_domain)
        rebuilt = canonical_hash({"tenant_id": block.tenant_id, "domain": block.data_domain, "batch_id": block.batch_id, "row_count": block.row_count, "merkle_root": block.merkle_root, "previous_hash": block.previous_hash, "created_at": block.created_at.isoformat()})
        if block.previous_hash != expected[key] or rebuilt != block.block_hash:
            invalid.append(block.id)
        expected[key] = block.block_hash
    return {"valid": not invalid, "blocks_checked": len(blocks), "invalid_block_ids": invalid}


def verify_current_snapshot(session) -> dict[str, object]:
    """Compare live records against the latest anchored root for each tenant/domain."""
    mismatches: list[dict] = []
    checked = 0
    for (tenant_id, domain), records in _tenant_partitions(session).items():
        latest = session.scalar(select(LedgerBlock).where(LedgerBlock.tenant_id == tenant_id, LedgerBlock.data_domain == domain).order_by(LedgerBlock.id.desc()))
        if latest is None:
            mismatches.append({"tenant_id": tenant_id, "data_domain": domain, "reason": "not anchored"})
            continue
        checked += 1
        if latest.merkle_root != merkle_root(records):
            mismatches.append({"tenant_id": tenant_id, "data_domain": domain, "reason": "data changed after latest anchor"})
    return {"valid": not mismatches, "partitions_checked": checked, "mismatches": mismatches}


def log_access(session, actor: str, tenant_id: str, action: str, resource: str) -> None:
    occurred_at = datetime.utcnow()
    event_hash = canonical_hash({"actor": actor, "tenant_id": tenant_id, "action": action, "resource": resource, "occurred_at": occurred_at.isoformat()})
    session.add(LedgerAccessEvent(actor=actor, tenant_id=tenant_id, action=action, resource=resource, occurred_at=occurred_at, event_hash=event_hash))
