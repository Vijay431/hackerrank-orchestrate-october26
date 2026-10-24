import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))

import ingest  # noqa: E402
import intent  # noqa: E402
import llm  # noqa: E402
import loader  # noqa: E402
import main as pipeline  # noqa: E402
import policy  # noqa: E402
import state  # noqa: E402
from ingest import Fact, SourceInfo  # noqa: E402


@pytest.fixture(scope="module")
def sample_rows():
    reqs = loader.load_samples()
    return pipeline.audit(reqs, {r.case_id: True for r in reqs}, None)


@pytest.fixture(scope="module")
def expected():
    with open(ROOT / "dataset" / "sample_output.csv", newline="", encoding="utf-8") as f:
        return {r["case_id"]: (r["deletion_status"], json.loads(r["steps_json"])) for r in csv.DictReader(f)}


def steps(rows, cid):
    return json.loads(rows[cid][1])


def key(s):
    return (s["phase"], s["system_id"], s["resource_id"], s["operation"])


# 6.2 ---------------------------------------------------------------
def test_parallel_matches_sequential(tmp_path):
    def transport(prompt, text, image):
        return json.dumps({"authorizes_deletion": "export" not in text.lower()}), 1, 1

    client = llm.LLMClient(transport, tmp_path / "c", tmp_path / "l.jsonl")
    reqs = loader.load_requests()[:40]
    par = intent.classify_all(client, reqs, lambda r: [])
    seq = {r.case_id: intent.classify(client, r, []) for r in reqs}
    assert par == seq


# 7.1 ---------------------------------------------------------------
def test_case_11_links_expected_resources(sample_rows):
    got = {s["resource_id"] for s in steps(sample_rows, "case_11")}
    assert {"search_052", "analytics_2034", "support_864", "data_flow_9522"} <= got


# 7.2 ---------------------------------------------------------------
def _index(facts, snaps=()):
    infos = {}
    for fid, cap, fs in facts:
        info = SourceInfo(fid, cap, f"evidence/databases/{fid}_20260101.sql", "sql", facts=fs)
        infos[fid] = info
    return state.FactIndex(infos)


def test_success_claim_contradicted_by_later_snapshot_is_present():
    early = Fact("e1", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", "search_service", "search_1", state="NOT_FOUND")
    late = Fact("e2", "2026-01-05T00:00:00Z", "2026-01-05T00:00:00Z", "search_service", "search_1", state="FOUND")
    idx = _index([("e1", early.captured_at, [early]), ("e2", late.captured_at, [late])])
    obs = state.observe("search_1", "search_service", "2026-01-10T00:00:00Z", idx)
    assert obs.state == "FOUND" and obs.source_id == "e2"
    obs = state.observe("search_1", "search_service", "2026-01-02T00:00:00Z", idx)
    assert obs.state == "NOT_FOUND"  # evidence after audit_at is ignored


def test_replica_keeps_record_after_primary_removal():
    primary = Fact("p", "2026-02-01T00:00:00Z", "2026-02-01T00:00:00Z", "account_service", "account_1", state="NOT_FOUND")
    replica = Fact("r", "2026-01-20T00:00:00Z", "2026-01-20T00:00:00Z", "account_service", "account_1", state="FOUND")
    pi = SourceInfo("p", primary.captured_at, "evidence/databases/primary_20260201.sql", "sql", facts=[primary])
    ri = SourceInfo("r", replica.captured_at, "evidence/databases/failover_replica_20260120.sql", "sql", facts=[replica])
    idx = state.FactIndex({"p": pi, "r": ri})
    assert state.observe("account_1", "account_service", "2026-03-01T00:00:00Z", idx).state == "FOUND"


# 7.3 ---------------------------------------------------------------
def test_statement_override_and_unresolved_count():
    infos = ingest.ingest_all([e for e in loader.load_evidence_manifest() if e.file_path.endswith("account_history_report_20260718.pdf")])
    f = next(x for x in next(iter(infos.values())).facts if x.resource_id == "NST-2026-0718-1842")
    assert (f.system_id, f.category) == ("account_history_service", "USER_PROFILE")
    pol = policy.Policy(loader.load_rules())
    assert pol.category("weird_1", []) == "UNRESOLVED" and pol.unresolved == 1


# 7.4 ---------------------------------------------------------------
@pytest.mark.parametrize("cid", ["case_31", "case_32", "case_09"])
def test_policy_treatment_samples(cid, sample_rows, expected):
    status, exp_steps = expected[cid]
    assert sample_rows[cid][0] == status
    want = {key(s) for s in exp_steps if s["system_id"] != "account_service"}
    got = {key(s) for s in steps(sample_rows, cid) if s["system_id"] != "account_service"}
    assert got == want


# 7.5 ---------------------------------------------------------------
@pytest.mark.parametrize("cid,op", [("case_15", "REPORT_ACTIVE_DATA_FLOW"), ("case_17", "REPORT_RESTORE_RISK")])
def test_recreation_risk(cid, op, sample_rows):
    assert any(s["operation"] == op for s in steps(sample_rows, cid))


# 8.1 / 8.2 -----------------------------------------------------------
def test_case_06_verifies_account_absent(sample_rows):
    assert any(s["operation"] == "VERIFY_RECORD_ABSENT" and s["resource_id"] == "account_006"
               for s in steps(sample_rows, "case_06"))


def test_case_11_order_matches_sample(sample_rows, expected):
    assert [key(s) for s in steps(sample_rows, "case_11")] == [key(s) for s in expected["case_11"][1]]
    assert [s["step_no"] for s in steps(sample_rows, "case_11")] == list(range(1, 15))


# 8.3 ---------------------------------------------------------------
def test_citations_match_samples_or_are_listed(sample_rows, expected):
    mismatches = []
    for cid, (_, exp_steps) in expected.items():
        got = {(s["resource_id"], s["operation"]): s["evidence_id"] for s in steps(sample_rows, cid)}
        for s in exp_steps:
            k = (s["resource_id"], s["operation"])
            if k in got and got[k] != s["evidence_id"]:
                mismatches.append((cid, k, s["evidence_id"], got[k]))
    assert mismatches == [], mismatches


# 9.2 ---------------------------------------------------------------
def test_usage_report_from_ledger(tmp_path, monkeypatch):
    import usage_report
    ledger = tmp_path / "l.jsonl"
    rows = [{"provider": "openrouter", "model": "m", "purpose": "intent", "cache_hit": False,
             "input_tokens": 100, "output_tokens": 10},
            {"provider": "openrouter", "model": "m", "purpose": "intent", "cache_hit": True,
             "input_tokens": 0, "output_tokens": 0}]
    ledger.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    monkeypatch.setenv("OPENROUTER_PRICE_INPUT", "1")
    monkeypatch.setenv("OPENROUTER_PRICE_OUTPUT", "2")
    per, purposes = usage_report.summarize(ledger)
    text = usage_report.render(per, purposes, 2)
    assert "| openrouter | m | 1 | 1 | 100 | 10 | 110 |" in text
    assert "Average tokens per request: 55.0" in text
