# Design

## Context

See proposal.md for motivation and specs/deletion-audit/spec.md for required behavior. Constraints that shape the approach:

- `code/main.py` and `code/evaluation/main.py` are empty; this is greenfield Python.
- Evidence: 94 files in `dataset/evidence/` (SQL snapshots, JSON bundles, logs, 4 PDFs, 11 PNGs). The manifest gives `captured_at` but not case membership.
- `system_activity.csv` (~4000 rows) mixes unrelated people; `reported_result` is SUCCESS/FAILED/PARTIAL and is only a claim.
- All 518 request emails resolve: 418 current, 100 historical.
- The `sqlite3` CLI is not installed; Python's `sqlite3` module is used instead.
- `deepseek/deepseek-v4-flash` is text-only; `deepseek/deepseek-v4.1-flash` accepts text and images and is the only allowed model (`openspec/config.yaml`).

## Goals / Non-Goals

**Goals:**
- Every decision except intent and image reading is plain code, so results are reproducible and explainable.
- A warm `.cache/` gives a fully offline, byte-identical rerun.

**Non-Goals:**
- No LLM reasoning over evidence for status or steps.
- No second model (`cloudflare/clef-flash` is out of scope).
- No use of hidden golden answers; no per-case tuning against the 32 samples.

## Decisions

### D1. Pipeline stages
```
load dataset --> ingest evidence (cached) --> build fact index
     |
     v
per case (parallel, 6 workers):
  intent (LLM, cached) --no--> NOT_APPLICABLE []
     | yes
  identity set --> linked resources --> state at audit_at
     --> policy treatment --> status --> steps --> serialize
     |
     v
collect, sort by case_id, write output.csv
```
The fact index is built once; each case filters it by identity set and `audit_at`. Alternative considered: an LLM agent per case reading raw evidence. Rejected for cost, nondeterminism, and weak evaluability.

### D2. Fact model
Every evidence source normalizes into one record shape: `(source_id, captured_at, system_id, resource_id, data_category_hint, subject_refs, identifier_fields, state_fields)`. `source_id` is the `file_id`, `activity_id`, or `audit_id`. SQL tables, JSON bundles, log lines, PDF text, and image extractions each get a parser that emits this shape. Alternative: case-specific ad hoc queries per format. Rejected because linking and time filtering would be duplicated per format.

### D3. Ingestion per format
- **SQL:** execute each file into an in-memory SQLite database; read every table; `snapshot_scope` rows give per-system snapshot times when present.
- **JSON / log / txt:** parse structure where present; otherwise regex-extract resource IDs (`<prefix>_<digits>`), emails, phones, hashes, `user_*` references.
- **PDF:** `pypdf` text extraction, cached at `.cache/evidence/<file_id>.txt`, then the same regex extraction.
- **PNG:** one `deepseek/deepseek-v4.1-flash` call per image with a fixed prompt requesting strict JSON (resource IDs, identifiers, visible states such as enabled/disabled, restore allowed). Cached at `.cache/evidence/<file_id>.json`.

### D4. Identity and linking
Identity set = `user_id` + all current and historical emails, phones, hashes (from `user_identities.csv` + `user_audit_log.csv`). Emails compared case-insensitively; phones compared after stripping non-digits. A resource links to the subject when a fact or a `LINK_RESOURCE_IDENTITY` event (at or before `audit_at`) puts its `resource_id` next to any identity value. Names are never sufficient alone.

### D5. State reconstruction
For each linked resource, take the latest fact at or before `audit_at` across all sources and replicas. A record present in any replica snapshot newer than its last observed removal counts as present (replica drift). Activity rows contribute risks (active sync, enabled connector, restore allowed) but never prove absence.

### D6. Policy table
`deletion_rules.csv` is loaded as data. A category resolver maps each resource to a category from its content (table name, `data_category_hint`, payload keys), with one fixed override: the account history statement PDF maps to `USER_PROFILE` with `system_id=account_history_service`, `resource_id=NST-2026-0718-1842`. Legal holds come only from `legal_hold_*` records; the finance register PDF only confirms activity of a hold. `SECURITY_AUDIT_LOG` follows `rule_12` using `retention_until` versus `audit_at`.

### D7. Step planning and ordering
Findings, remediations, and verifications are generated from (resource, required state, observed state) triples, then sorted by a fixed operation rank (the problem statement table order), `system_id`, `resource_id`, and renumbered. Remediation order (flows and restores before records) falls out of the operation rank. Serialization uses `json.dumps(sort_keys=True, separators=(",", ":"))`.

### D8. Citation rule
Per resource, cite the latest file captured at or before `audit_at` that covers that resource's system (a file whose records or `snapshot_scope` include the system) and proves the resource's observed state, including absence in a snapshot that covers the system. FINDING and COMPLETE verification steps cite that file; steps for resources in the same system share it. Activity or audit IDs are cited only when no file covers the finding. Rationale: sample `case_04` cites `evidence_54` for its account step and `evidence_56` for its analytics step, so one file per case cannot match.

### D9. LLM client and cache
OpenRouter SDK client, temperature 0, fixed prompts stored as files under `code/prompts/`. Cache key = SHA-256 of `model + prompt text + input`. Cache stored as JSON files under `.cache/llm/`. Usage (input/output tokens, cache hit or miss) is appended to a run ledger used by the usage report.

### D10. Parallelism
A thread pool with 6 workers runs per-case work; results are collected into a dict keyed by `case_id` and written in sorted order, so concurrency never affects output order. Image extraction runs before cases start.

### D11. Evaluation harness (built first)
The harness is built before the pipeline and scores whatever `output.csv` exists (a stub at first), so every later task reports a score. Metrics, each 0-100:
- **Status accuracy:** share of the 32 sample cases whose `deletion_status` matches.
- **Step accuracy:** share of expected steps matched exactly (all 7 fields) at the same position.
- **Field accuracy:** share of matching fields across position-aligned steps; missing or extra steps count as all fields wrong.
- **Sequence accuracy:** share of cases whose ordered `(phase, operation, system_id, resource_id)` list matches exactly.
- **Citation validity:** share of non-empty `evidence_id` values in the 32-row sample output (the evaluation never runs the 518 evaluation requests) that resolve to a manifest `file_id`, `activity_id`, or `audit_id` with timestamp at or before the case's `audit_at`.
- **Determinism:** the pipeline runs twice; 100 if both `output.csv` files are byte-identical, else 0, with differing rows listed.

Headline = 0.25 status + 0.20 step + 0.15 field + 0.20 sequence + 0.10 citation + 0.10 determinism. The command prints every metric and the headline, writes them to `evaluation/evaluation_report.md`, and always exits 0 (report only, no gate). Custom cases are stored as small CSV fixtures under `code/evaluation/cases/` with expected outputs and reported separately.

### D12. Developer commands
A root `Makefile` is a thin alias layer; it adds no logic. `PY ?= .venv/bin/python`, overridable.
- `install`: create `.venv`, `pip install -r code/requirements.txt`
- `run`: `code/main.py` then `code/validate_output.py` (submission run, intent gate on)
- `dev`: `code/main.py --assume-deletion` then `code/evaluation/main.py --offline` (no API key)
- `eval`: `code/evaluation/main.py`
- `validate`, `test` (`pytest tests`), `usage` (`code/usage_report.py`), `package` (`code/package.py`)
- `graph`: `graphify update .` to re-extract code into `graphify-out/` without LLM calls

AGENTS.md §8 says do not assume bash, so Make is a convenience only and README keeps the raw commands. Windows users run those directly.

## Risks / Trade-offs

- [Category resolver misclassifies a resource, e.g. analytics record needing DELETE vs ANONYMIZE] -> Derive category from content fields, log every unresolved category, and surface counts in the evaluation report.
- [Image extraction quality varies] -> Strict JSON prompt, cached once, results cross-checked against SQL/JSON facts for the same resource.
- [Per-resource citation rule mismatches hidden answers for some cases] -> Validated against all 32 samples; mismatches recorded under failures in the evaluation report.
- [Overfitting to 32 samples] -> Rules expressed generically; custom cases exercise behaviors not present in the samples.
- [OpenRouter rate limits or transient errors] -> Bounded retries with backoff; failed calls are never cached.
- [Early harness runs score a stub output, so headline scores start near zero] -> Scores are tracked per task in the report; only the trend matters until the pipeline is complete.
- [Model or prompt change invalidates cache] -> Model and prompt are part of the cache key, so stale entries are never reused.

## Migration Plan

Not applicable: new code, no existing behavior.

## Open Questions

- OpenRouter per-token prices for `deepseek/deepseek-v4.1-flash` are read at report time from the public models endpoint; if unavailable, the usage report states that cost is an estimate from the last known price.
