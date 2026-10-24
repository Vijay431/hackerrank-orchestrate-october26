import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))

import llm  # noqa: E402


def make(tmp_path, transport):
    return llm.LLMClient(transport, tmp_path / "c", tmp_path / "ledger.jsonl", sleep=lambda s: None)


def test_second_call_is_cache_hit(tmp_path):
    calls = []

    def t(p, x, i):
        calls.append(1)
        return "ok", 10, 2

    c = make(tmp_path, t)
    assert c.complete("p", "x") == "ok"
    assert c.complete("p", "x") == "ok"
    assert len(calls) == 1
    rows = [json.loads(l) for l in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    assert [r["cache_hit"] for r in rows] == [False, True]
    assert rows[0]["input_tokens"] == 10 and rows[1]["input_tokens"] == 0


def test_retry_then_success_and_failure_not_cached(tmp_path):
    n = {"i": 0}

    def flaky(p, x, i):
        n["i"] += 1
        if n["i"] == 1:
            raise ConnectionError("boom")
        return "fine", 1, 1

    c = make(tmp_path, flaky)
    assert c.complete("p", "x") == "fine" and n["i"] == 2

    def always(p, x, i):
        raise ConnectionError("down")

    c2 = make(tmp_path, always)
    with pytest.raises(llm.LLMError):
        c2.complete("p", "other")
    assert not any("other" in f.read_text() for f in (tmp_path / "c").glob("*.json"))


def test_missing_key_warm_cache_works_and_key_never_stored(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-secret-123")
    c = make(tmp_path, lambda p, x, i: ("r", 1, 1))
    c.complete("p", "x")
    monkeypatch.delenv("OPENROUTER_API_KEY")
    c_real = llm.LLMClient(cache_dir=tmp_path / "c", ledger=tmp_path / "ledger.jsonl")
    assert c_real.complete("p", "x") == "r"
    with pytest.raises(llm.LLMError):
        c_real.complete("p", "uncached")
    for f in tmp_path.rglob("*"):
        if f.is_file():
            assert "sk-secret-123" not in f.read_text()
