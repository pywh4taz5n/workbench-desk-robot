from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from initialize_approval_signatures import (
    BOARD_PATH,
    BOM_PATH,
    REPO_ROOT,
    SIGNATURE_FIELDS,
    SIGNATURE_REGISTER,
    SOURCE_REGISTER,
    board_revision,
    read_csv,
    sha256_file,
    validate_signature_register,
)


class RoleApprovalError(ValueError):
    pass


def record_role_approval(
    references: list[str],
    role: str,
    signed_by: str,
    signed_at: str,
    evidence_ref: str,
    *,
    source_path: Path = SOURCE_REGISTER,
    signature_path: Path = SIGNATURE_REGISTER,
    bom_path: Path = BOM_PATH,
    board_path: Path = BOARD_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, object]:
    if not references or len(references) != len(set(references)):
        raise RoleApprovalError("one or more unique references are required")
    if not role.endswith(" Owner"):
        raise RoleApprovalError("role must be an explicit ... Owner role")
    if not signed_by.strip():
        raise RoleApprovalError("signed_by is required")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", signed_at):
        raise RoleApprovalError("signed_at must use YYYY-MM-DD")
    if not evidence_ref.strip() or not (repo_root / evidence_ref).is_file():
        raise RoleApprovalError(f"approval evidence does not exist: {evidence_ref!r}")

    approvals = read_csv(source_path)
    signatures = read_csv(signature_path)
    revision = board_revision(board_path)
    bom_hash = sha256_file(bom_path)
    before = validate_signature_register(approvals, signatures, revision, bom_hash, repo_root)
    if not before["pass"]:
        raise RoleApprovalError("signature register is not bound to the current board revision and BOM")

    targets = {(reference, role) for reference in references}
    matched: set[tuple[str, str]] = set()
    updated: list[dict[str, str]] = []
    for row in signatures:
        key = (row.get("reference", ""), row.get("role", ""))
        if key not in targets:
            updated.append(row.copy())
            continue
        if row.get("decision") != "PENDING" or any(
            row.get(field, "").strip() for field in ("signed_by", "signed_at", "evidence_ref")
        ):
            raise RoleApprovalError(f"role row {key!r} already contains a decision or evidence")
        approved = row.copy()
        approved.update(
            {
                "decision": "APPROVED",
                "signed_by": signed_by,
                "signed_at": signed_at,
                "evidence_ref": evidence_ref,
            }
        )
        updated.append(approved)
        matched.add(key)
    if matched != targets:
        raise RoleApprovalError(f"required role rows are missing: {sorted(targets - matched)}")

    temporary = signature_path.with_suffix(signature_path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SIGNATURE_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(updated)
    temporary.replace(signature_path)
    after = validate_signature_register(approvals, updated, revision, bom_hash, repo_root)
    if not after["pass"]:
        raise RoleApprovalError("recorded role approvals did not validate")
    return {
        "approved_role_rows": len(matched),
        "references": sorted(references),
        "role": role,
        "hardware_revision": revision,
        "bom_sha256": bom_hash,
        "approved_signature_count": after["approved_signature_count"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Record an attributed PCB role approval against the current BOM")
    parser.add_argument("--reference", action="append", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--signed-by", required=True)
    parser.add_argument("--signed-at", required=True)
    parser.add_argument("--evidence-ref", required=True)
    args = parser.parse_args()
    report = record_role_approval(
        args.reference,
        args.role,
        args.signed_by,
        args.signed_at,
        args.evidence_ref,
    )
    print(
        f"recorded {report['approved_role_rows']} {report['role']} approvals for "
        f"{', '.join(report['references'])}; BOM {report['bom_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
