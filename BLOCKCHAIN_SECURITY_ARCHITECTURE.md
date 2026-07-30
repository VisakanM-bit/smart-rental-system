# FleetSight integrity ledger and permissioned blockchain integration

## What is protected

FleetSight creates tenant-aware, append-only integrity proofs. It commits SHA-256/Merkle-root proofs per tenant and data domain: rental, telemetry, customer, machine, and maintenance. Each proof chains to the previous proof for the same tenant/domain.

Any edit, deletion, insertion, or value change in protected data changes the recomputed Merkle root. The Integrity ledger page reports this as **Changed since anchor**. A broken stored block or previous-hash link reports as **Compromised**.

## Privacy boundary

The ledger never holds raw GPS coordinates, telemetry, phone numbers, names, rental rates, deposits, or fault descriptions. It stores only tenant IDs, row counts, timestamps, Merkle roots, prior hashes, and block hashes. Raw data stays in the operational database.

## Multi-customer protection

Blockchain proofing is one control; production requires all of these:

1. Enforce tenant scope (`customer_id`) in every API query and row-level database policy.
2. Give customer accounts only tenant-scoped roles; separately audit privileged access.
3. Encrypt databases, backups, and network transport; use a managed KMS for keys.
4. Use the hash chain and Merkle proofs to detect silent historical-data alteration.
5. Keep append-only access evidence for integrity actions.
6. Apply consent, retention, and sharing policy outside the immutable proof layer.

Blockchain cannot prevent an authorised person from copying data they can legitimately view. Least privilege, export controls, watermarking, contracts, and audit monitoring address that risk.

## Demo workflow

1. Open **Integrity ledger**.
2. Confirm **Chain status: Verified** and **Live snapshot: Matches anchor**.
3. Explain that only hashes—not customer data—appear in the ledger.
4. Create a new integrity snapshot only after an approved import or correction.
5. Explain that unapproved database modification creates a Merkle-root mismatch.

## Production Hyperledger Fabric path

The prototype runs immediately with `LEDGER_MODE=hash-chain`. For a consortium deployment, use a company-controlled Node.js or Java Fabric Gateway with mTLS, certificate rotation, endorsement policies, and private-data collections. Configure `FABRIC_GATEWAY_URL` and `FABRIC_API_TOKEN` as deployment secrets. `app/services/fabric_anchor.py` submits only proof metadata.

The gateway endpoint receives `tenant_id`, `data_domain`, `batch_id`, `row_count`, `merkle_root`, `previous_hash`, `block_hash`, and `created_at`. It must reject raw records and authenticate application and tenant identity. Never embed Fabric certificates, keys, or tokens in source code or Streamlit session state.
