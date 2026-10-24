# Tasks

## 1. Baseline

- [x] 1.1 Revert `code/paths.py` with `git checkout -- code/paths.py` and restore the root file with `git checkout -- output.csv`. Verify `git status` no longer lists either file.
- [x] 1.2 Record the baseline: the file count of `.cache/llm/`, the line count of `.cache/usage_ledger.jsonl`, `sha256sum output.csv`, and the current headline score from `evaluation/evaluation_report.md`. Verify all four values are written down for group 5.

## 2. Makefile and tests

- [x] 2.1 Remove the `test` and `graph` targets and remove `test`, `graph` and `dev` from `.PHONY` in `Makefile`. Verify `make help` lists only `help install run eval validate usage package`.
- [x] 2.2 Delete `tests/` and `.pytest_cache/`, remove the `.pytest_cache/` line from `.gitignore`, and remove `"tests"` from INCLUDE in `code/package.py`. Verify `make package` succeeds and its listing has no `tests/` entry.
- [x] 2.3 Remove the pytest, `make test` and `make graph` lines from `README.md`, and replace the `make graph` instruction in `AGENTS.md` §10 with the raw `graphify update .` command. Verify that grepping both files for `pytest`, `make test` and `make graph` finds nothing.

## 3. Pipeline CLI and intent

- [x] 3.1 In `code/main.py`, remove `--stub` and `--assume-deletion` with their branches, the unused `activity = loader.load_activity()` in the intent branch, and the `lambda r: []` argument to `classify_all`. Keep `--requests` and `--output`. Verify `python code/main.py --help` lists only `--requests` and `--output`.
- [x] 3.2 In `code/intent.py`, remove `prior_classifications`, the `context` parameter of `classify` and `classify_all`, the `if context:` branch, and any imports this leaves unused (`Iterable`, `Activity`). Verify the text built for a request is still exactly `"<request_text>\n{body}\n</request_text>"`.
- [x] 3.3 In `code/llm.py`, make `LLMClient.__init__` take no parameters and assign `_openrouter_transport`, `CACHE_DIR`, `LEDGER` and `time.sleep` directly. Drop the `Transport` alias if nothing else uses it. Verify `python -c "import sys; sys.path.insert(0,'code'); import llm; llm.LLMClient()"` succeeds.

## 4. Evaluation and helper CLIs

- [x] 4.1 In `code/evaluation/main.py`, remove `--offline`, the `OFFLINE` global and the `--assume-deletion` append, remove `--label` (use the constant `run`) and `--no-report` (always write the report), drop `argparse` if it is now unused, and fix the usage docstring. Verify that grepping `code/evaluation/main.py` for `argparse`, `OFFLINE`, `--label` and `--no-report` finds nothing. (Do not run it with `--help`: without a parser, that would start a full evaluation.)
- [x] 4.2 Remove the optional ledger argument from `code/usage_report.py` and the optional out/request arguments from `code/validate_output.py`, and keep each module's own defaults. Verify `make validate` and `make usage` succeed.
- [x] 4.3 Remove the `make dev` row and the offline-mode paragraphs from `README.md` (the `--assume-deletion` / `--offline` text). Note that keyless runs need a warm `.cache/`. Verify that grepping `README.md` for `make dev`, `--offline` and `--assume-deletion` finds nothing.

## 5. Integration check

- [x] 5.1 Run `make run`. Verify it reports 518 rows with 0 problems and that `sha256sum output.csv` matches the 1.2 baseline.
- [x] 5.2 Run `make eval`. Verify the headline score equals the 1.2 baseline and that `evaluation/evaluation_report.md` was rewritten.
- [x] 5.3 Verify that the `.cache/llm/` file count equals the 1.2 baseline and that every ledger line added after the baseline has `"cache_hit": true`.
- [x] 5.4 Grep the repo, excluding `openspec/changes/archive/`, `log.txt` and `graphify-out/`, for `--offline`, `--assume-deletion`, `--stub`, `--label`, `--no-report`, `make test`, `make graph`, `make dev`, `pytest` and `prior_classifications`. Verify there are no hits outside this change's own artifacts.

## Workflow follow-up

- Refresh `graphify-out/` with `graphify update .` after the code changes, per AGENTS.md §10.
- Archive the change with `/opsx:archive` after review.
