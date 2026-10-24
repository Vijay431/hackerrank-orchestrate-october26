# Design

## Context

See proposal.md (Why). The change touches nine modules, the Makefile and two docs, but removes code only. The one runtime-sensitive point is the LLM response cache: `LLMClient.complete` keys each response on `cache_key(MODEL, prompt, payload)`, where `payload` is the text built by `intent.classify`. A warm `.cache/llm/` is what lets `make run` and `make eval` finish without an API key and without new model calls.

## Goals / Non-Goals

**Goals:**
- Every remaining Makefile target and CLI flag has a caller in the `run` or `eval` paths.
- `output.csv` and the evaluation scores are unchanged, and no new model calls are made.

**Non-Goals:**
- No change to audit, policy, planning or evaluation logic, prompts, or the output contract.
- No new test framework. The golden-sample evaluation stays the only verification.
- No dead-code sweep beyond the items listed in the proposal.

## Decisions

- **Drop the intent `context` parameter instead of keeping it as an extension point.** It is always empty, so `classify` never appends `prior_intake_classifications`, and the text sent to the model is just the fenced `request_text`. Removing the branch leaves that text byte-identical, so every cache key is unchanged. The alternative, keeping the parameter for a possible future prior-classification feature, is speculative; `prior_classifications` was never wired in.
- **Inline the `LLMClient` defaults.** `__init__` keeps no parameters: it uses `_openrouter_transport`, `CACHE_DIR`, `LEDGER` and `time.sleep` directly, and `self.*` reads stay where they are. That way only the constructor changes and the call sites in `complete` stay as they are. Keeping the injectable seams was rejected because the tests were their only callers.
- **Keep `--requests` and `--output` on `code/main.py`.** `code/evaluation/main.py` runs the pipeline as a subprocess on `sample_deletion_requests.csv` and `code/evaluation/cases/requests.csv` and writes to temporary files. Replacing that with an in-process call would be a refactor, not a removal.
- **Hardcode the history label as `run`, and always write the report.** `make eval` already passes no flags, so this matches current behavior exactly.
- **Revert `code/paths.py` with git, not by hand.** `git checkout -- code/paths.py` restores the committed `OUTPUT = ROOT / "output.csv"`. Then `make run` regenerates the root `output.csv`, which is the gated submission run.

## Risks / Trade-offs

- [The intent prompt text changes by accident, which turns every cache entry into a miss and triggers a full set of paid calls] → Record the file count of `.cache/llm/` before editing. After `make run` and `make eval`, the count must be the same, and the new ledger entries must all have `cache_hit: true`. (Unsetting the env var is not enough: `code/llm.py` falls back to `.env`.)
- [Losing keyless cold-cache runs] → Accepted. The README states that a warm `.cache/` is needed for keyless runs.
- [Stale references to removed flags or targets] → Before finishing, grep for `--offline`, `--assume-deletion`, `--stub`, `--label`, `--no-report`, `make test`, `make graph`, `make dev`, `pytest` and `prior_classifications`; outside `openspec/changes/archive/` and `log.txt`, there must be no hits.

## Migration Plan

All work lands in one commit, and `git revert` rolls it back.
