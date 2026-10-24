import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))

import ingest  # noqa: E402
import loader  # noqa: E402

MANIFEST = {Path(e.file_path).name: e for e in loader.load_evidence_manifest()}


def run(name, client=None):
    return ingest.ingest_file(MANIFEST[name], client)


def test_sql_audit_record_retention():
    info = run("customer_data_inventory_20260916.sql")
    f = next(x for x in info.facts if x.resource_id == "audit_record_1738")
    assert f.attrs["retention_until"].startswith("2031-12-31")
    assert f.system_id == "security_service" and f.observed_at == "2026-09-16T08:37:39Z"
    assert info.coverage["account_service"] == "2026-09-16T08:37:39Z"


def test_json_log_text_extraction():
    j = run("security_audit_ledger_20261001.json")
    assert any(f.resource_id == "account_1733" and "haruka-kato@gmail.com" in f.refs for f in j.facts)
    lg = run("resource_lookup_trace_20260926_103856.log")
    f = next(x for x in lg.facts if x.resource_id == "account_2064" and x.state)
    assert "charlotte.wright@outlook.com" in f.refs and f.state == "NOT_FOUND"
    t = run("customer_account_handover_20261001.txt")
    f = next(x for x in t.facts if x.resource_id == "account_4248")
    assert f.state == "NOT_FOUND" and "novak.tomasz@icloud.com" in f.refs


def test_pdf_retention_extract():
    info = run("security_retention_extract.pdf")
    f = next(x for x in info.facts if x.resource_id == "audit_record_003")
    assert "user_03" in f.refs and f.attrs["retain_until"] == "25 Aug 2027"


def test_every_manifest_file_ingested_or_skipped():
    for name, ef in MANIFEST.items():
        info = ingest.ingest_file(ef)
        assert info.facts or info.coverage or info.skipped, name
