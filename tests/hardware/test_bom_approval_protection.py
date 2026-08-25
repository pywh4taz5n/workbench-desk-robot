from __future__ import annotations

import csv
import hashlib
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "hardware/pcb/tools"


def load_generator():
    sys.path.insert(0, str(TOOLS))
    try:
        path = TOOLS / "generate_bom.py"
        spec = importlib.util.spec_from_file_location("generate_bom_protection", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(TOOLS))


def load_signature_initializer():
    path = TOOLS / "initialize_approval_signatures.py"
    spec = importlib.util.spec_from_file_location("approval_signature_initializer", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_eco_migrator():
    sys.path.insert(0, str(TOOLS))
    try:
        path = TOOLS / "migrate_approval_eco.py"
        spec = importlib.util.spec_from_file_location("approval_eco_migrator", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(TOOLS))


def load_role_approval_recorder():
    sys.path.insert(0, str(TOOLS))
    try:
        path = TOOLS / "record_role_approval.py"
        spec = importlib.util.spec_from_file_location("role_approval_recorder", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(TOOLS))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_initialize_creates_and_then_preserves_pristine_pending_register(tmp_path: Path) -> None:
    module = load_generator()
    rows = [
        {
            field: value
            for field, value in {
                "reference": "U1",
                "candidate": "TBD",
                "required_approver": "Electrical Owner",
                "decision": "PENDING",
                "approved_mpn": "",
                "datasheet_revision": "",
                "approved_by": "",
                "approved_at": "",
                "evidence_ref": "",
            }.items()
        }
    ]
    approval_path = tmp_path / "component-approval-register.csv"
    signature_path = tmp_path / "component-approval-signatures.csv"

    assert module.initialize_approval_register(rows, approval_path, signature_path)
    assert not module.initialize_approval_register(rows, approval_path, signature_path)
    assert list(csv.DictReader(approval_path.open(newline="", encoding="utf-8"))) == rows


def test_initialize_rejects_signed_or_manually_changed_registers(tmp_path: Path) -> None:
    module = load_generator()
    rows = [
        {
            "reference": "U1",
            "candidate": "TBD",
            "required_approver": "Electrical Owner",
            "decision": "PENDING",
            "approved_mpn": "",
            "datasheet_revision": "",
            "approved_by": "",
            "approved_at": "",
            "evidence_ref": "",
        }
    ]
    approval_path = tmp_path / "component-approval-register.csv"
    signature_path = tmp_path / "component-approval-signatures.csv"
    write_rows(approval_path, [{**rows[0], "approved_mpn": "MURATA-1"}])
    try:
        module.initialize_approval_register(rows, approval_path, signature_path)
    except RuntimeError as exc:
        assert "recorded approvals" in str(exc)
    else:
        raise AssertionError("signed approval register was overwritten")

    write_rows(approval_path, [{**rows[0], "candidate": "MANUAL-TBD"}])
    try:
        module.initialize_approval_register(rows, approval_path, signature_path)
    except RuntimeError as exc:
        assert "manually changed" in str(exc)
    else:
        raise AssertionError("manually changed pending register was overwritten")

    write_rows(approval_path, rows)
    signature_rows = [
        {
            "reference": "U1",
            "candidate": "TBD",
            "role": "Electrical Owner",
            "decision": "APPROVED",
            "signed_by": "Owner",
            "signed_at": "2026-08-22",
            "evidence_ref": "evidence.txt",
            "hardware_revision": "EVT1",
            "bom_sha256": "hash",
        }
    ]
    write_rows(signature_path, signature_rows)
    try:
        module.initialize_approval_register(rows, approval_path, signature_path)
    except RuntimeError as exc:
        assert "signed role evidence" in str(exc)
    else:
        raise AssertionError("signed role register was reinitialized")


def test_bom_hash_is_stable_across_lf_and_crlf(tmp_path: Path) -> None:
    module = load_signature_initializer()
    content = b"reference,quantity\nU1,1\n"
    lf_path = tmp_path / "bom-lf.csv"
    crlf_path = tmp_path / "bom-crlf.csv"
    cr_path = tmp_path / "bom-cr.csv"
    lf_path.write_bytes(content)
    crlf_path.write_bytes(content.replace(b"\n", b"\r\n"))
    cr_path.write_bytes(content.replace(b"\n", b"\r"))

    assert module.sha256_file(lf_path) == module.sha256_file(crlf_path)
    assert module.sha256_file(lf_path) == module.sha256_file(cr_path)


def _write_signature_fixture(
    tmp_path: Path,
    signature_rows: list[dict[str, str]],
    bom_bytes: bytes = b"reference,quantity\nU1,1\n",
) -> tuple[Path, Path, Path, Path]:
    source_path = tmp_path / "component-approval-register.csv"
    signature_path = tmp_path / "component-approval-signatures.csv"
    bom_path = tmp_path / "bom.csv"
    board_path = tmp_path / "controller.kicad_pcb"
    source_rows = [
        {
            "reference": "U1",
            "candidate": "TBD",
            "required_approver": "Electrical Owner",
        }
    ]
    write_rows(source_path, source_rows)
    write_rows(signature_path, signature_rows)
    bom_path.write_bytes(bom_bytes)
    board_path.write_text('(kicad_pcb\n  (general\n    (thickness 1.6)\n  )\n  (rev "EVT1")\n)\n', encoding="utf-8")
    return source_path, signature_path, bom_path, board_path


def test_initialize_rebinds_only_pristine_pending_bom_hashes(tmp_path: Path) -> None:
    module = load_signature_initializer()
    source_rows = [{"reference": "U1", "candidate": "TBD", "required_approver": "Electrical Owner"}]
    bom_bytes = b"reference,quantity\r\nU1,1\r\n"
    # Build the signature row from the same generated fields, then simulate a
    # pre-normalization hash left by a Windows checkout.
    expected = module.expected_signature_rows(source_rows, "EVT1", "placeholder")[0]
    expected["bom_sha256"] = hashlib.sha256(bom_bytes).hexdigest()
    source_path, signature_path, bom_path, board_path = _write_signature_fixture(tmp_path, [expected], bom_bytes)
    expected_hash = module.sha256_file(bom_path)

    report = module.initialize_register(source_path, signature_path, bom_path, board_path)

    assert report["rebound_signature_rows"] == 1
    assert report["pass"] is True
    rebound = list(csv.DictReader(signature_path.open(newline="", encoding="utf-8")))
    assert rebound[0]["bom_sha256"] == expected_hash


def test_initialize_refuses_signed_or_manually_changed_hash_migrations(tmp_path: Path) -> None:
    module = load_signature_initializer()
    source_rows = [{"reference": "U1", "candidate": "TBD", "required_approver": "Electrical Owner"}]
    bom_bytes = b"reference,quantity\r\nU1,1\r\n"
    expected = module.expected_signature_rows(source_rows, "EVT1", "placeholder")[0]
    expected["bom_sha256"] = hashlib.sha256(bom_bytes).hexdigest()
    source_path, signature_path, bom_path, board_path = _write_signature_fixture(tmp_path, [expected], bom_bytes)

    signed = expected.copy()
    signed.update({"signed_by": "Owner", "signed_at": "2026-08-22", "evidence_ref": "evidence.txt"})
    write_rows(signature_path, [signed])
    try:
        module.initialize_register(source_path, signature_path, bom_path, board_path)
    except module.ApprovalRegisterError as exc:
        assert "signed or modified" in str(exc)
    else:
        raise AssertionError("signed role row was silently rebound")

    manually_changed = expected.copy()
    manually_changed["candidate"] = "MANUAL-TBD"
    write_rows(signature_path, [manually_changed])
    try:
        module.initialize_register(source_path, signature_path, bom_path, board_path)
    except module.ApprovalRegisterError as exc:
        assert "signed or modified" in str(exc)
    else:
        raise AssertionError("manually changed row was silently rebound")


def test_explicit_eco_migrates_only_pristine_pending_candidates_and_hashes() -> None:
    module = load_eco_migrator()
    expected_approval = {
        "reference": "U1",
        "candidate": "NEW-CANDIDATE",
        "required_approver": "Electrical Owner",
        "decision": "PENDING",
        "approved_mpn": "",
        "datasheet_revision": "",
        "approved_by": "",
        "approved_at": "",
        "evidence_ref": "",
    }
    existing_approval = {**expected_approval, "candidate": "OLD-CANDIDATE"}
    existing_signature = {
        "reference": "U1",
        "candidate": "OLD-CANDIDATE",
        "role": "Electrical Owner",
        "decision": "PENDING",
        "signed_by": "",
        "signed_at": "",
        "evidence_ref": "",
        "hardware_revision": "EVT1",
        "bom_sha256": "old-hash",
    }

    approvals, signatures, changes = module.plan_migration(
        [expected_approval], [existing_approval], [existing_signature], "EVT1", "new-hash"
    )

    assert approvals[0]["candidate"] == "NEW-CANDIDATE"
    assert signatures[0]["candidate"] == "NEW-CANDIDATE"
    assert signatures[0]["bom_sha256"] == "new-hash"
    assert {change["role"] for change in changes} == {"SELECTION_REGISTER", "Electrical Owner"}


def test_explicit_eco_refuses_any_signed_role_or_selection() -> None:
    module = load_eco_migrator()
    approval = {
        "reference": "U1",
        "candidate": "CANDIDATE",
        "required_approver": "Electrical Owner",
        "decision": "PENDING",
        "approved_mpn": "",
        "datasheet_revision": "",
        "approved_by": "",
        "approved_at": "",
        "evidence_ref": "",
    }
    signature = {
        "reference": "U1",
        "candidate": "CANDIDATE",
        "role": "Electrical Owner",
        "decision": "APPROVED",
        "signed_by": "Owner",
        "signed_at": "2026-08-25",
        "evidence_ref": "evidence.txt",
        "hardware_revision": "EVT1",
        "bom_sha256": "old-hash",
    }
    try:
        module.plan_migration([approval], [approval], [signature], "EVT1", "new-hash")
    except module.ApprovalMigrationError as exc:
        assert "signed or modified" in str(exc)
    else:
        raise AssertionError("signed role row was migrated")

    signed_selection = {**approval, "decision": "APPROVED", "approved_mpn": "CANDIDATE"}
    pending_signature = {**signature, "decision": "PENDING", "signed_by": "", "signed_at": "", "evidence_ref": ""}
    try:
        module.plan_migration([approval], [signed_selection], [pending_signature], "EVT1", "new-hash")
    except module.ApprovalMigrationError as exc:
        assert "signed or modified" in str(exc)
    else:
        raise AssertionError("signed selection row was migrated")


def test_role_approval_records_only_the_requested_owner_against_current_bom(tmp_path: Path) -> None:
    initializer = load_signature_initializer()
    module = load_role_approval_recorder()
    source_path = tmp_path / "component-approval-register.csv"
    signature_path = tmp_path / "component-approval-signatures.csv"
    bom_path = tmp_path / "bom.csv"
    board_path = tmp_path / "controller.kicad_pcb"
    evidence_path = tmp_path / "system-owner-authorization.md"
    source_rows = [{"reference": "J1", "candidate": "CONNECTOR", "required_approver": "System Owner"}]
    bom_path.write_text("reference,quantity\nJ1,1\n", encoding="utf-8")
    board_path.write_text('(kicad_pcb\n  (rev "EVT1")\n)\n', encoding="utf-8")
    evidence_path.write_text("System Owner authorization\n", encoding="utf-8")
    write_rows(source_path, source_rows)
    signature_rows = initializer.expected_signature_rows(
        source_rows,
        "EVT1",
        initializer.sha256_file(bom_path),
    )
    write_rows(signature_path, signature_rows)

    report = module.record_role_approval(
        ["J1"],
        "System Owner",
        "Quchaosheng",
        "2026-08-25",
        evidence_path.name,
        source_path=source_path,
        signature_path=signature_path,
        bom_path=bom_path,
        board_path=board_path,
        repo_root=tmp_path,
    )

    assert report["approved_role_rows"] == 1
    recorded = list(csv.DictReader(signature_path.open(newline="", encoding="utf-8")))
    assert recorded[0]["decision"] == "APPROVED"
    assert recorded[0]["signed_by"] == "Quchaosheng"
    assert recorded[0]["bom_sha256"] == initializer.sha256_file(bom_path)


def test_role_approval_rejects_unlisted_or_already_signed_roles(tmp_path: Path) -> None:
    initializer = load_signature_initializer()
    module = load_role_approval_recorder()
    source_path = tmp_path / "component-approval-register.csv"
    signature_path = tmp_path / "component-approval-signatures.csv"
    bom_path = tmp_path / "bom.csv"
    board_path = tmp_path / "controller.kicad_pcb"
    evidence_path = tmp_path / "authorization.md"
    source_rows = [{"reference": "J1", "candidate": "CONNECTOR", "required_approver": "System Owner"}]
    bom_path.write_text("reference,quantity\nJ1,1\n", encoding="utf-8")
    board_path.write_text('(kicad_pcb\n  (rev "EVT1")\n)\n', encoding="utf-8")
    evidence_path.write_text("authorization\n", encoding="utf-8")
    write_rows(source_path, source_rows)
    write_rows(
        signature_path,
        initializer.expected_signature_rows(source_rows, "EVT1", initializer.sha256_file(bom_path)),
    )
    arguments = {
        "signed_by": "Quchaosheng",
        "signed_at": "2026-08-25",
        "evidence_ref": evidence_path.name,
        "source_path": source_path,
        "signature_path": signature_path,
        "bom_path": bom_path,
        "board_path": board_path,
        "repo_root": tmp_path,
    }

    try:
        module.record_role_approval(["J1"], "Electrical Owner", **arguments)
    except module.RoleApprovalError as exc:
        assert "required role rows are missing" in str(exc)
    else:
        raise AssertionError("an unlisted role was approved")

    module.record_role_approval(["J1"], "System Owner", **arguments)
    try:
        module.record_role_approval(["J1"], "System Owner", **arguments)
    except module.RoleApprovalError as exc:
        assert "already contains a decision or evidence" in str(exc)
    else:
        raise AssertionError("an approved role was signed twice")
