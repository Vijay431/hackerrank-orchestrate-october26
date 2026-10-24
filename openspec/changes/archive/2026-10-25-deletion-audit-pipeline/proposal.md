# Proposal

## Why

Northstar Shop's deletion workflow reports "Complete" while personal data survives in replicas, indexes, exports, support records, analytics, and backups, and active syncs or restores can recreate it. The challenge requires a terminal-runnable agent that audits all 518 requests in `dataset/deletion_requests.csv` from evidence, not workflow claims, and writes a graded `output.csv` plus evaluation and usage reports. No solution code exists yet (`code/main.py` is empty).

## What Changes

- Add a deterministic Python audit pipeline, run from the terminal, that reads only `dataset/` and writes `output.csv` (518 rows, sorted by `case_id`) at the repository root.
- Add a request-intent gate: one LLM call per case (`deepseek/deepseek-v4.1-flash` via OpenRouter, temperature 0, cached) deciding whether `request_text` authorizes deletion; non-deletion cases become `NOT_APPLICABLE` with `[]`.
- Add evidence ingestion for every file in `dataset/evidence_files.csv`: PDFs via `pypdf`, PNGs via one cached multimodal call per image, SQL snapshots via SQLite, JSON/log/text parsed directly. All derived artifacts cached under `.cache/`.
- Add identity resolution over current and historical email, phone, and email hash; resource linking through catalog link events and evidence contents.
- Add state reconstruction at `audit_at` (inclusive), ignoring later evidence and treating reported statuses/results as claims.
- Add a policy engine applying `deletion_rules.csv`, including account tombstones, legal holds backed by real `legal_hold_*` records, security-audit retention, and backup restore blocking.
- Add a step planner emitting FINDING, REMEDIATION, VERIFICATION steps in the contract's fixed order and schema.
- Build the evaluation harness first; it reports a weighted headline score combining sample accuracy, citation validity, and determinism.
- Add an evaluation harness scoring against `dataset/sample_output.csv` and participant-authored cases, plus a determinism check, producing `evaluation/evaluation_report.md` and `evaluation/usage_report.md`.
- Add a root `Makefile` wrapping the documented commands (`install`, `run`, `dev`, `eval`, `validate`, `test`, `usage`, `package`, `graph`); the README's plain `python` commands stay the canonical, shell-independent path.
- Add a "Skill usage" section to `AGENTS.md`: agents use caveman for terse replies and query `graphify-out/` before broad codebase searches, refreshing the graph with `make graph` after code changes.

## Capabilities

### New Capabilities
- `deletion-audit`: Auditing a deletion request end to end: intent classification, evidence ingestion, identity resolution, resource linking, state at `audit_at`, policy application, step planning, output serialization, and the evaluation and usage reports that prove it.

### Modified Capabilities
<!-- None: no existing specs in openspec/specs/. -->

## Impact

- New code under `code/` (entry point `code/main.py`, evaluation under `code/evaluation/`).
- New dependencies: `pypdf`, OpenRouter SDK; Python stdlib `sqlite3`, `csv`, `json`, `concurrent` features.
- New runtime cache directory `.cache/` at the repository root (must be git-ignored and excluded from `code.zip`).
- Requires `OPENROUTER_API_KEY` in the environment; never committed or logged.
- Outputs: `output.csv`, `evaluation/evaluation_report.md`, `evaluation/usage_report.md`; `README.md` gains setup and run instructions.
- Hidden organizer answers are never used; evaluation uses only `dataset/sample_output.csv` and custom cases.
- New root `Makefile` (included in `code.zip`); `AGENTS.md` gains a skill-usage section; `graphify-out/` refreshed via `graphify update`.
