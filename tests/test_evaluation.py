import json
import sys
from pathlib import Path

import importlib.util

CODE = Path(__file__).resolve().parent.parent / "code"
sys.path.insert(0, str(CODE))
_spec = importlib.util.spec_from_file_location("eval_main", CODE / "evaluation" / "main.py")
ev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ev)


def step(**kw):
    base = dict(step_no=1, phase="VERIFICATION", system_id="s", resource_id="r",
                operation="VERIFY_RECORD_ABSENT", state="ABSENT", evidence_id="e1")
    base.update(kw)
    return base


def row(cid, status, steps):
    return {"case_id": cid, "deletion_status": status, "steps_json": json.dumps(steps)}


def test_perfect_match_scores_100():
    r = [row("c1", "COMPLETE", [step()])]
    m = ev.score_outputs(r, r)
    assert all(v == 100 for v in m.values())


def test_wrong_field_lowers_field_and_step():
    exp = [row("c1", "COMPLETE", [step()])]
    got = [row("c1", "COMPLETE", [step(evidence_id="e2")])]
    m = ev.score_outputs(exp, got)
    assert m["status"] == 100 and m["sequence"] == 100
    assert m["step"] == 0 and m["field"] == pytest_approx(600 / 7)


def pytest_approx(x):
    import pytest
    return pytest.approx(x)


def test_future_dated_citation_is_flagged():
    ids = {"e_ok": "2026-01-01T00:00:00Z", "e_late": "2026-12-01T00:00:00Z"}
    out = [row("c1", "COMPLETE", [step(evidence_id="e_ok"), step(step_no=2, evidence_id="e_late"),
                                  step(step_no=3, evidence_id="nope")])]
    score, bad = ev.citation_validity(out, {"c1": "2026-06-01T00:00:00Z"}, ids)
    assert score < 100
    assert bad == [("c1", "e_late"), ("c1", "nope")]


def test_determinism():
    a = [row("c1", "COMPLETE", [step()])]
    assert ev.determinism(a, a) == (100.0, [])
    b = [row("c1", "INCOMPLETE", [step()])]
    assert ev.determinism(a, b) == (0.0, ["c1"])


def test_headline_formula():
    m = {"status": 100, "step": 50, "field": 80, "sequence": 60, "citation": 100, "determinism": 0}
    assert ev.headline(m) == pytest_approx(25 + 10 + 12 + 12 + 10 + 0)
