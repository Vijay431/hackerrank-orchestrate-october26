"""Write evaluation/usage_report.md from the usage ledger of the last run.

The ledger (.cache/usage_ledger.jsonl) holds one line per model call or cache hit.
Prices come from the environment (USD per million tokens) because they change:
OPENROUTER_PRICE_INPUT and OPENROUTER_PRICE_OUTPUT. Without them cost is reported as unknown.
"""
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from llm import LEDGER  # noqa: E402
from paths import EVAL_DIR  # noqa: E402


def summarize(ledger: Path):
    per = defaultdict(lambda: {"calls": 0, "hits": 0, "in": 0, "out": 0})
    purposes = defaultdict(int)
    if ledger.exists():
        for line in ledger.read_text(encoding="utf-8").splitlines():
            e = json.loads(line)
            m = per[(e["provider"], e["model"])]
            if e["cache_hit"]:
                m["hits"] += 1
            else:
                m["calls"] += 1
                m["in"] += e["input_tokens"]
                m["out"] += e["output_tokens"]
                purposes[e.get("purpose", "")] += 1
    return per, purposes


def render(per, purposes, requests: int) -> str:
    pin, pout = os.environ.get("OPENROUTER_PRICE_INPUT"), os.environ.get("OPENROUTER_PRICE_OUTPUT")
    L = ["# Usage Report", "", f"Requests in the final run: {requests}", "",
         "| Provider | Model | Model calls | Cache hits | Input tokens | Output tokens | Total tokens | Est. cost (USD) |",
         "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    tc = ti = to = th = 0
    cost_total = 0.0
    known = bool(pin and pout)
    for (prov, model), m in sorted(per.items()):
        total = m["in"] + m["out"]
        cost = (m["in"] * float(pin) + m["out"] * float(pout)) / 1e6 if known else None
        cost_total += cost or 0.0
        L.append(f"| {prov} | {model} | {m['calls']} | {m['hits']} | {m['in']} | {m['out']} | {total} | "
                 f"{'%.4f' % cost if cost is not None else 'unknown'} |")
        tc += m["calls"]; ti += m["in"]; to += m["out"]; th += m["hits"]
    L.append(f"| **All** | | **{tc}** | **{th}** | **{ti}** | **{to}** | **{ti + to}** | "
             f"**{'%.4f' % cost_total if known else 'unknown'}** |")
    n = max(requests, 1)
    L += ["", f"- Average tokens per request: {(ti + to) / n:.1f}",
          f"- Estimated cost per request: {('%.6f' % (cost_total / n)) if known else 'unknown'} USD",
          f"- Calls by purpose: {dict(purposes) or 'none'}",
          "- Cost uses `OPENROUTER_PRICE_INPUT` / `OPENROUTER_PRICE_OUTPUT` (USD per million tokens) from the environment."
          if known else "- Prices were not provided, so cost is reported as unknown.", ""]
    return "\n".join(L)


def main():
    import loader
    per, purposes = summarize(LEDGER)
    EVAL_DIR.mkdir(exist_ok=True)
    (EVAL_DIR / "usage_report.md").write_text(render(per, purposes, len(loader.load_requests())), encoding="utf-8")
    print("wrote", EVAL_DIR / "usage_report.md")


if __name__ == "__main__":
    main()
