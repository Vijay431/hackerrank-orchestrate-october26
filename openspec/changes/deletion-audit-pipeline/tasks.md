# Tasks

From group 3 onward, every task's verification also includes: run `python code/evaluation/main.py` and record the score in the report.

## 1. Setup

- [x] 1.1 Create `code/requirements.txt` with `pypdf` and the OpenRouter SDK; verify `pip install -r code/requirements.txt` succeeds in a fresh venv
- [x] 1.2 Add `.cache/` to `.gitignore` and confirm `OPENROUTER_API_KEY` is listed in `.env.example`; verify with `git check-ignore .cache/x`
- [x] 1.3 Create the module layout under `code/` (loader, ingest, identity, state, policy, planner, llm, main) with repo-root-relative paths; verify `python code/main.py --help` runs

## 2. Evaluation harness (first)

- [x] 2.1 Make `code/main.py` write a stub `output.csv` (518 rows, `NOT_APPLICABLE`, `[]`) so the harness has input; verify 518 sorted rows
- [x] 2.2 Implement `code/evaluation/main.py` scoring status, step, field, and sequence accuracy against `dataset/sample_output.csv` per D11; verify it prints all four metrics for the stub
- [x] 2.3 Implement citation validity over the full output (known id, timestamp at or before `audit_at`), listing offending cases; verify a fixture with a future-dated citation scores below 100
- [x] 2.4 Implement the determinism check (two pipeline runs, byte comparison, differing rows listed); verify the stub scores 100
- [x] 2.5 Compute the headline score (0.25 status, 0.20 step, 0.15 field, 0.20 sequence, 0.10 citation, 0.10 determinism) and always exit 0; verify the formula with a unit test
- [ ] 2.6 Add at least three custom cases under `code/evaluation/cases/` (non-deletion request, historical-email subject, tombstone or replica-drift case) with expected outputs; verify they run and are reported separately
- [x] 2.7 Write metrics, headline, custom-case results, and a score history table to `evaluation/evaluation_report.md`; verify all required sections are present

## 3. Dataset loading and identity

- [ ] 3.1 Load all dataset CSVs into typed records; verify row counts (518 requests, 32 samples, 15 rules) in a unit test
- [ ] 3.2 Implement identity resolution (current + historical email, phone, hash; case-insensitive email, digit-only phone); verify all 518 request emails resolve (418 current, 100 historical) in a test
- [ ] 3.3 Document identity rules in `README.md`; verify the section exists

## 4. LLM client and cache

- [ ] 4.1 Implement the OpenRouter client for `deepseek/deepseek-v4.1-flash` at temperature 0 with SHA-256 keyed cache under `.cache/llm/` and a usage ledger; verify a test with a stubbed client shows a second call is a cache hit with zero model calls
- [ ] 4.2 Add bounded retry with backoff that never caches failures; verify with a stub that fails once then succeeds
- [ ] 4.3 Ensure the API key is read only from the environment and never written to cache, ledger, or logs; verify by grepping `.cache/` after a run

## 5. Evidence ingestion

- [ ] 5.1 SQL ingestion via Python `sqlite3` into the common fact shape, including `snapshot_scope` times; verify a test extracts `audit_record_1738` with `retention_until` 2031-12-31 from `customer_data_inventory_20260916.sql`
- [ ] 5.2 JSON, log, and text ingestion with identifier regex extraction; verify a test finds known resource IDs and emails in one file of each type
- [ ] 5.3 PDF ingestion via `pypdf` cached at `.cache/evidence/<file_id>.txt`; verify `security_retention_extract.pdf` yields `audit_record_003`, `user_03`, and retain-until 2027-08-25
- [ ] 5.4 Image extraction prompt in `code/prompts/` and one cached call per PNG to `.cache/evidence/<file_id>.json`; verify all 11 images produce valid JSON and a rerun makes zero calls
- [ ] 5.5 Build the fact index with `captured_at` from the manifest; verify every manifest `file_id` is ingested or explicitly reported as skipped

## 6. Intent gate

- [ ] 6.1 Intent prompt in `code/prompts/` returning strict JSON `{"authorizes_deletion": bool}`, with prior `CLASSIFY_REQUEST` events as context; verify all 32 sample requests classify as deletion (matching `sample_output.csv`) and three custom non-deletion texts (access, export, opt-out) classify as non-deletion
- [ ] 6.2 Run intent calls in a 6-worker pool keyed by `case_id`; verify parallel and sequential runs give identical decisions

## 7. Linking, state, and policy

- [ ] 7.1 Resource linking via `LINK_RESOURCE_IDENTITY` events and fact contents, cut off at `audit_at`; verify sample case `case_11` links `search_052`, `analytics_2034`, `support_864`, `data_flow_9522`
- [ ] 7.2 State at `audit_at` (inclusive), latest observation wins, replica drift, claims ignored; verify a test where a SUCCESS deletion is contradicted by a later snapshot yields PRESENT
- [ ] 7.3 Category resolver from content plus the account-history statement override (`USER_PROFILE`, `account_history_service`, `NST-2026-0718-1842`); verify unresolved categories are logged and counted
- [ ] 7.4 Policy treatment from `deletion_rules.csv` including tombstone, `legal_hold_*`-only holds with register confirmation, `rule_12` retention, and backup restore blocking; verify sample cases `case_31`, `case_32`, `case_09` treatments
- [ ] 7.5 Recreation-risk detection (active flows, restorable backups); verify sample cases `case_15` and `case_17`

## 8. Step planning and output

- [ ] 8.1 Status decision and step generation for COMPLETE and INCOMPLETE cases, with verification for every linked resource; verify `case_06` includes VERIFY_RECORD_ABSENT for `account_006`
- [ ] 8.2 Fixed ordering (phase, operation rank, `system_id`, `resource_id`) and renumbering; verify `case_11` step order matches `sample_output.csv`
- [ ] 8.3 Single-file citation rule (latest covering capture at or before `audit_at`); verify cited `evidence_id` matches all 32 samples or mismatches are listed
- [ ] 8.4 Write `output.csv` (sorted, compact sorted-key JSON, NOT_APPLICABLE as `[]`), replacing the stub; verify 518 rows, valid JSON, allowed operation/state pairs via a validator script
- [ ] 8.5 Document setup and run commands in `README.md`; verify a clean run following the README produces `output.csv`

## 9. Final reports

- [ ] 9.1 Add failures found and improvements made to `evaluation/evaluation_report.md` from the score history; verify the section is present
- [ ] 9.2 Generate `evaluation/usage_report.md` from the usage ledger of the final full run (provider, model, calls, cache hits, tokens, totals, averages, cost estimates); verify it covers all required fields

## 10. Integration

- [ ] 10.1 Run the full 518-case pipeline from a cold cache, then again from a warm cache; verify byte-identical `output.csv` and zero model calls on the second run
- [ ] 10.2 Run the final evaluation and record the headline score; verify determinism is 100
- [ ] 10.3 Confirm the `code.zip` contents exclude `dataset/`, `.cache/`, venvs, and secrets; verify by listing the archive
