from __future__ import annotations

import argparse
import csv
import hashlib
import io
import re
from pathlib import Path

from generate_bom import build_rows
from initialize_approval_signatures import (
    SIGNATURE_FIELDS,
    board_revision,
    expected_signature_rows,
)

PCB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PCB_ROOT.parents[1]
BOM_PATH = PCB_ROOT / "fabrication" / "bom.csv"
APPROVAL_PATH = PCB_ROOT / "component-approval-register.csv"
SIGNATURE_PATH = PCB_ROOT / "component-approval-signatures.csv"
BOARD_PATH = PCB_ROOT / "kicad" / "controller.kicad_pcb"
MIGRATION_LOG_PATH = PCB_ROOT / "approval-eco-migrations.csv"
BOM_FIELDS = ["reference", "quantity", "function", "design_candidate", "package_or_module", "procurement_gate"]
APPROVAL_FIELDS = [
    "reference",
    "candidate",
    "required_approver",
    "decision",
    "approved_mpn",
    "datasheet_revision",
    "approved_by",
    "approved_at",
    "evidence_ref",
]
MIGRATION_FIELDS = [
    "migration_id",
    "applied_at",
    "reference",
    "role",
    "action",
    "old_candidate",
    "new_candidate",
    "old_bom_sha256",
    "new_bom_sha256",
    "hardware_revision",
    "reason",
    "evidence_ref",
]


class ApprovalMigrationError(ValueError):
    pass


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def csv_text(rows: list[dict[str, str]], fields: list[str]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def normalized_sha256(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _approval_key(row: dict[str, str]) -> str:
    return row.get("reference", "")


def _signature_key(row: dict[str, str]) -> tuple[str, str]:
    return row.get("reference", ""), row.get("role", "")


def _unique_by_key(rows: list[dict[str, str]], key_fn, label: str) -> dict[object, dict[str, str]]:
    indexed: dict[object, dict[str, str]] = {}
    for row in rows:
        key = key_fn(row)
        if not key or key in indexed:
            raise ApprovalMigrationError(f"{label} contains a blank or duplicate key: {key!r}")
        indexed[key] = row
    return indexed


def _is_pristine_approval(row: dict[str, str]) -> bool:
    return row.get("decision") == "PENDING" and all(
        not row.get(field, "").strip()
        for field in ("approved_mpn", "datasheet_revision", "approved_by", "approved_at", "evidence_ref")
    )


def _is_pristine_signature(row: dict[str, str]) -> bool:
    return row.get("decision") == "PENDING" and all(
        not row.get(field, "").strip() for field in ("signed_by", "signed_at", "evidence_ref")
    )


def plan_migration(
    expected_approvals: list[dict[str, str]],
    existing_approvals: list[dict[str, str]],
    existing_signatures: list[dict[str, str]],
    hardware_revision: str,
    bom_sha256: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    expected_approval_by_key = _unique_by_key(expected_approvals, _approval_key, "expected approval register")
    existing_approval_by_key = _unique_by_key(existing_approvals, _approval_key, "existing approval register")
    stale_approval_keys = set(existing_approval_by_key) - set(expected_approval_by_key)
    if stale_approval_keys:
        raise ApprovalMigrationError(f"stale approval rows require a reviewed ECO: {sorted(stale_approval_keys)}")
    for reference, row in existing_approval_by_key.items():
        if not _is_pristine_approval(row):
            raise ApprovalMigrationError(f"approval row {reference!r} is signed or modified and cannot be migrated")

    expected_signatures = expected_signature_rows(expected_approvals, hardware_revision, bom_sha256)
    expected_signature_by_key = _unique_by_key(expected_signatures, _signature_key, "expected signature register")
    existing_signature_by_key = _unique_by_key(existing_signatures, _signature_key, "existing signature register")
    stale_signature_keys = set(existing_signature_by_key) - set(expected_signature_by_key)
    if stale_signature_keys:
        raise ApprovalMigrationError(f"stale signature rows require a reviewed ECO: {sorted(stale_signature_keys)}")
    for key, row in existing_signature_by_key.items():
        if not _is_pristine_signature(row):
            raise ApprovalMigrationError(f"signature row {key!r} is signed or modified and cannot be migrated")

    changes: list[dict[str, str]] = []
    for expected in expected_approvals:
        old = existing_approval_by_key.get(expected["reference"])
        if old != expected:
            changes.append(
                {
                    "reference": expected["reference"],
                    "role": "SELECTION_REGISTER",
                    "action": "ADD_PENDING_SELECTION" if old is None else "MIGRATE_PRISTINE_PENDING_SELECTION",
                    "old_candidate": "" if old is None else old.get("candidate", ""),
                    "new_candidate": expected["candidate"],
                    "old_bom_sha256": "",
                    "new_bom_sha256": bom_sha256,
                }
            )
    for expected in expected_signatures:
        key = _signature_key(expected)
        old = existing_signature_by_key.get(key)
        if old != expected:
            changes.append(
                {
                    "reference": expected["reference"],
                    "role": expected["role"],
                    "action": "ADD_PENDING_ROLE" if old is None else "MIGRATE_PRISTINE_PENDING_ROLE",
                    "old_candidate": "" if old is None else old.get("candidate", ""),
                    "new_candidate": expected["candidate"],
                    "old_bom_sha256": "" if old is None else old.get("bom_sha256", ""),
                    "new_bom_sha256": bom_sha256,
                }
            )
    return expected_approvals, expected_signatures, changes


def _atomic_write(path: Path, text: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="")
    temporary.replace(path)


def apply_migration(
    migration_id: str,
    applied_at: str,
    reason: str,
    evidence_ref: str,
    *,
    bom_path: Path = BOM_PATH,
    approval_path: Path = APPROVAL_PATH,
    signature_path: Path = SIGNATURE_PATH,
    board_path: Path = BOARD_PATH,
    migration_log_path: Path = MIGRATION_LOG_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, object]:
    if not re.fullmatch(r"ECO-[A-Za-z0-9._-]+", migration_id):
        raise ApprovalMigrationError("migration_id must use the ECO-... form")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", applied_at):
        raise ApprovalMigrationError("applied_at must use YYYY-MM-DD")
    if not reason.strip():
        raise ApprovalMigrationError("migration reason is required")
    evidence_path = repo_root / evidence_ref
    if not evidence_ref.strip() or not evidence_path.is_file():
        raise ApprovalMigrationError(f"migration evidence does not exist: {evidence_ref!r}")

    bom_rows, expected_approvals = build_rows()
    bom_text = csv_text(bom_rows, BOM_FIELDS)
    bom_hash = normalized_sha256(bom_text)
    revision = board_revision(board_path)
    approvals, signatures, changes = plan_migration(
        expected_approvals,
        read_csv(approval_path),
        read_csv(signature_path),
        revision,
        bom_hash,
    )
    existing_log = read_csv(migration_log_path)
    if any(row.get("migration_id") == migration_id for row in existing_log):
        raise ApprovalMigrationError(f"migration id already exists: {migration_id}")
    log_rows = [
        *existing_log,
        *[
            {
                "migration_id": migration_id,
                "applied_at": applied_at,
                **change,
                "hardware_revision": revision,
                "reason": reason,
                "evidence_ref": evidence_ref,
            }
            for change in changes
        ],
    ]
    _atomic_write(bom_path, bom_text)
    _atomic_write(approval_path, csv_text(approvals, APPROVAL_FIELDS))
    _atomic_write(signature_path, csv_text(signatures, SIGNATURE_FIELDS))
    _atomic_write(migration_log_path, csv_text(log_rows, MIGRATION_FIELDS))
    return {
        "migration_id": migration_id,
        "hardware_revision": revision,
        "bom_sha256": bom_hash,
        "approval_row_count": len(approvals),
        "signature_row_count": len(signatures),
        "change_count": len(changes),
        "migration_log_row_count": len(log_rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Explicitly migrate pristine pending PCB approval rows for an ECO")
    parser.add_argument("--apply", action="store_true", help="write the planned pristine-only migration")
    parser.add_argument("--migration-id", required=True)
    parser.add_argument("--applied-at", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--evidence-ref", required=True)
    args = parser.parse_args()
    if not args.apply:
        raise ApprovalMigrationError("refusing to change approval bindings without --apply")
    report = apply_migration(
        args.migration_id,
        args.applied_at,
        args.reason,
        args.evidence_ref,
    )
    print(
        f"applied {report['migration_id']}: {report['change_count']} recorded changes, "
        f"{report['approval_row_count']} approvals, {report['signature_row_count']} role rows, "
        f"BOM {report['bom_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
