# Tasks

## 1. Price constant and report

- [x] 1.1 Add `PRICE_PER_M = (0.02, 1.0)` beside `MODEL` in `code/llm.py`; verify `python -c "import sys;sys.path.insert(0,'code');import llm;print(llm.PRICE_PER_M)"` prints it
- [x] 1.2 In `code/usage_report.py`, price from env override else `llm.PRICE_PER_M`; drop the `unknown` branches; add a line stating input/output price per 1M and its source; verify `make usage` shows total ≈ 0.0950 USD and per-request ≈ 0.000183 USD for the current ledger
- [x] 1.3 Update the usage paragraph in `README.md` (default price, env override) and verify it matches behavior
- [x] 1.4 Commit regenerated `evaluation/usage_report.md`; verify no `unknown` remains in it
