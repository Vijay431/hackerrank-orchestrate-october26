# 04 Evaluation harness, timing diagnostic, custom cases, tests (top repo)

Repo: /tmp/top/ghost-data-still-exists (read-only analysis; no repo code executed; no log.txt appended per read-only instruction)

## Evaluation harness (metrics computed: case-level, step-level, field-level, sequence; how scored; CLI)

File: /tmp/top/ghost-data-still-exists/evaluation/main.py (92 lines)

- Keys: `KEYS = ("phase", "operation", "system_id", "resource_id", "state", "evidence_id")` (main.py:13); `FIELDS = ("step_no", *KEYS)` (main.py:14).
- Loader `read()` (main.py:17-20): `csv.DictReader` with `utf-8-sig`, keyed by `case_id`, `steps_json` parsed with `json.loads`.
  - Gap: duplicate `case_id` rows are silently overwritten by the dict comprehension. The coverage check at main.py:26-27 (`set(pred) != set(gold)`) cannot detect duplicates.
- `score()` (main.py:23-72), cases iterated in sorted order (main.py:31):
  - Case-level status accuracy: `equal_status` and `status += equal_status` (main.py:33-34).
  - Exact row match: `exact += a == b` (main.py:36). This compares the whole dict, including `steps_json` order and `step_no`, so it is order-sensitive.
  - Sequence accuracy: `sequence +=` a boolean that compares the ordered tuples of `KEYS` (main.py:37). `step_no` is excluded here.
  - Step-level set metrics (main.py:38-42): `Counter` multiset intersection over `KEYS` tuples. Gives `tp`, `pp`, `gp`. Order-insensitive. Precision, recall and F1 at main.py:59-64.
  - Field-level accuracy (main.py:44-47): positional `zip(a_steps, b_steps)`, per field in `FIELDS`. Gap: `zip` truncates, so unmatched extra or missing steps do not add to the field denominator. A single inserted step shifts every later position and is then scored as field mismatches.
  - Mismatch diagnostics (main.py:48-58): `causes` Counter for "status", "missing steps", "extra steps". Each mismatched case is printed as `cid status ... expected ... missing [...] extra [...]`.
- Printed output (main.py:66-71): `exact_rows`, `status_accuracy`, `step_precision`, `step_recall`, `step_f1`, `sequence_accuracy`, one `field <name> correct / total ratio` line per field, and `causes`.
- The function returns a `result` dict (main.py:61-65), but the CLI discards it. No JSON or Markdown metrics file is written. This matters because `evaluation/evaluation_report.md` is a required submission artifact (AGENTS.md section 6.8).
- CLI (main.py:75-92):
  - Positional `predictions` is optional. Default answers are `--answers`, else `<dataset>/sample_output.csv` (main.py:82).
  - With predictions given, it scores that CSV directly.
  - With no predictions, it runs `main.py --offline --sample --dataset <d> --run-dir <tmp>` in a temp dir (main.py:86-89), then scores `sample_predictions.csv`. So the no-argument path only covers the sample (public) requests, not the 518 evaluation requests.
  - Non-zero exit from the subprocess raises `RuntimeError` with the tail of stdout and stderr (main.py:90-91).
- README usage: `README.md:232-233` shows `python evaluation/main.py --dataset evaluation/custom_cases/tombstone_pii --answers evaluation/custom_cases/tombstone_pii/sample_output.csv`.

## Timing diagnostic (what it measures and why)

File: /tmp/top/ghost-data-still-exists/evaluation/timing_diagnostic.py (105 lines)

Purpose (docstring line 1): check worker timing on evaluation requests where accounts are linked independently of identity tokens. It is a checker of timing hypotheses, not a scorer. No test file I read imports it.

Pipeline, `diagnose()` (timing_diagnostic.py:26-94):
1. Transcribes evidence with `transcribe_all(dataset, manifest, Path("runs/final"), offline=True)` (line 28). The run dir is hardcoded; the CLI has no `--run-dir`.
2. Builds observations from `load()` plus `activity_links()` (lines 29-30). Builds `IdentityIndex` (lines 31-32).
3. For each request in `deletion_requests.csv` (line 41), it finds "linked" `(system, resource_id)` pairs. The window is `requested - 30 days` to `audit + 7 days`, using `file_captured_at` (lines 45-47).
4. Account deletions: `DELETE_RECORD` on `account_service` within `[report - 2h, report + 15min]` for the linked accounts (lines 48-51). Only cases with exactly one such delete are checked (line 52).
5. Checks on that single delete:
   - "Account window" (line 56): lead time `report - delete` must be in 40 to 80 minutes.
   - "Reported result" (lines 57-58): `delete.reported_result == STATUS_RESULT[reported_status]`.
6. "First follow-up" (lines 64-79): follow-up events from non-account linked resources, plus `SYNC_RECORD` checkpoints whose details contain "Replication worker reported its final checkpoint for account_". The offset is `(first.second - delete.second) % 60`. Expected values are 51 or 52 (line 77).
7. Policy-action offsets (lines 81-93), keyed by `POLICY_OFFSETS` (lines 17-23):
   - `REDACT_RECORD / support_platform`: {49, 50}
   - `BLOCK_RESTORE / backup_service`: {50, 51}
   - `DISABLE_DATA_FLOW / integration_service`: {20, 21}
   - `RETAIN_RECORD / legal_service`: {19, 20}
   - `ANONYMIZE_RECORD / analytics_platform`: {19, 20}
   Each event's details must contain "Policy action completed for" and its resource must be linked. Offset is `(delete.second - event.second) % 60`.

Output (lines 102-105): a table `rule | checkable | agree | observed offsets | exceptions`. CLI takes only `--dataset` (lines 98-100).

Why it exists: it tests whether the worker's second-level scheduling pattern is stable enough to use as a linking signal. The same constants (`policy_offset`, `second_distance`, the 40 to 80 minute window) appear in `ghost/activity.py`, as the unit tests import them (`tests/test_ghost.py:7`, `tests/test_ghost.py:77-78`, `tests/test_ghost.py:112`). I did not open `ghost/activity.py` to confirm they are identical.

Caveat: the constants are hardcoded magic numbers fitted to this dataset. Treat them as overfitting risk. The diagnostic runs over all 518 evaluation requests (`deletion_requests.csv`), so it is the one harness that touches the full set. It needs `dataset/`, which is absent in this checkout.

## Custom cases (table: folder | scenario tested | expected status | key trap it guards against)

Folder: /tmp/top/ghost-data-still-exists/evaluation/custom_cases/<name>/. Each folder has one request row in `deletion_requests.csv`, identical to `sample_deletion_requests.csv` (checked with `cmp`), plus `sample_output.csv`, `system_activity.csv`, `user_identities.csv`, `user_audit_log.csv`, `deletion_rules.csv` (16 lines each), `evidence_files.csv` and `evidence/records/evidence_0N.json`. Expected rows are asserted in `tests/test_submission.py:29-37`.

| folder | scenario tested | expected status (sample_output.csv) | key trap it guards against |
|---|---|---|---|
| after_audit | `evidence_01` (09:00Z, NOT_FOUND on `search_2`) is before `audit_at` 2026-09-03T10:00Z. `evidence_02` (11:00Z, FOUND) is after audit. | COMPLETE. One VERIFICATION step, `VERIFY_RECORD_ABSENT` on `search_2`, cites `evidence_01` only. | Later recreation after `audit_at` must not change the answer. Cutoff enforced in validator and resources. |
| historical_replica | Request email is the new address. The old address (`audit_1` email change) is found FOUND on `customer_search_read_replica` at 08:05Z. Primary says NOT_FOUND at 08:00Z. | INCOMPLETE. FINDING `REPORT_REMAINING_RECORD` on `search_1` (cites evidence_01). REMEDIATION `DELETE_RECORD`. VERIFICATION `VERIFY_RECORD_ABSENT`. | Historical email must resolve to the same subject. Replica drift: a primary NOT_FOUND does not prove absence on a replica. |
| non_deletion | Request text "Please export my data; do not delete my account." A deletion keyword is present, but the request is negated. Evidence shows `account_3` FOUND. | NOT_APPLICABLE, `steps_json=[]`. | Negated deletion and export requests must not be classified as deletion. |
| timed_analytics | `analytics_5` has no identifying tokens. It is linked only by timing: `DELETE_RECORD` on `account_5` at 09:30:10Z, `ANONYMIZE_RECORD` on `analytics_5` at 09:35:51Z. Evidence: `account_5` NOT_FOUND, `analytics_5` ANONYMIZED. | COMPLETE. Two VERIFICATION steps: `VERIFY_RECORD_ABSENT` (account_5), `VERIFY_RECORD_ANONYMIZED` (analytics_5). | Anonymous analytics records must be linked through activity timing alone, and that linkage must not be taken as proof of state. |
| tombstone_pii | `tombstone_4` still holds `user_id`, name, and the email `tombstone_pii@example.test` (evidence_01). Retained stable reference, direct identifiers exposed. | INCOMPLETE. FINDING `REPORT_EXPOSED_PII`, REMEDIATION `REDACT_RECORD`, VERIFICATION `VERIFY_RECORD_REDACTED`. All on `tombstone_4`. | Tombstones keep the subject reference but must lose direct identifiers. Do not delete the tombstone. |

## Unit/integration tests (count of test functions per file; list what each group asserts; any fixtures/mocks of LLM)

Config: `pyproject.toml` sets `pythonpath = ["."]`, `testpaths = ["tests"]`. CI: `.github/workflows/tests.yml` runs `python -m pytest -q` on Python 3.11 after `pip install -r requirements.txt` (openai==3.37.0, pypdf==6.10.0, pytest==8.3.4, httpx2==2.16.0).

### tests/test_agent.py: 24 test functions (lines 29 to 456), plus helpers

Helpers and fakes:
- `setup_case()` (line 52): builds a request, one `Observation`, and a `plan()` row. Returns `AgentTools`, `AgentConfig`, and the row.
- `class Scripted` (line 71): fake model. Its `ask(messages)` pops scripted tool names and returns `function_call` items. `"error"` raises `ProviderFailure`. `"final"` returns an empty message. Used with `AgentRuntime` (line 104) and in the tests at lines 202, 208, 220, 231, 243, 344 and 389.
- `httpx2.MockTransport` (lines 306-317): captures the real OpenAI SDK request body. This is a wire-format test, not an LLM mock.
- `class FakeClient` (lines 431-446): fake `responses.create` returning three scripted items. Used in `test_replay_and_deterministic_rows_agree` (line 418).
- `SimpleNamespace` clients: `Broken` (line 255, raises `RuntimeError`), `Counting` (line 267, asserts no call), `Incomplete` (line 331, `status="incomplete"`).

What the groups assert:
- Tool-protocol and cache serialization: lines 29, 41, 284, 296. Function-call request shape, stable token order in `resolve_subject`, truncated cache tail tolerated with a warning, opaque bytes escaped in the cache file. The escaping test (296-303) builds the sentinel at runtime "so the compiled test file stays clean". This suggests a secret-scanner concern.
- Tool loop and gate: lines 108, 115, 124, 144, 158, 170, 188, 202. Clean path, policy lookup exposes no resource IDs or finished plans, gate canonicalizes only order and numbers, gate recomputes policy from facts, unresolved resources are visible to the gate, empty inspection shows the snapshot scope, non-deletion stops after classification.
- Rejection and fallback: lines 208, 220, 231, 243. Hallucinated resource rejected three times then falls back to the deterministic row (`gate_rejection_cap`). Future citation rejected ("after cutoff"). Injected instruction in source text changes nothing. Tool cap fallback. Provider error fallback.
- Transport and cost: lines 253, 266, 306, 329. Circuit opens after 3 errors. Budget gate blocks before the provider call. Pinned SDK asserts `model == "gpt-6-luna"`, `reasoning.effort == "low"`, `tool_choice == "required"`, 8 tools, `strict: True`. Incomplete responses still write a usage receipt with `cost_usd > 0` and are not cached.
- Ambiguity and batch correlation: lines 344, 389. Ambiguous account choice needs a distinguishing source. Joint reassignment is blocked. Linked policy activity can distinguish a batch candidate.
- Replay: lines 418, 456. Live run (3 fresh calls) and offline replay (3 cached calls, 0 fresh) must produce identical results. Line 456 is an HTTP server end-to-end check on `case_533`, skipped when `dataset/` is absent.

### tests/test_ghost.py: 14 test methods in one `unittest.TestCase` class (`GhostControls`, line 26)

Methods at lines 27, 38, 48, 80, 114, 119, 127, 135, 140, 149, 163, 171, 176, 185.
- Mock: `unittest.mock.patch("ghost.intake.ask", return_value=(answer, None, False))` (line 31). This is the only LLM mock in the file. It fakes the intake classifier to disagree with a negated request, then checks that the guard keeps the case and records a conflict.
- Dataset-dependent: line 38 (`test_catalog_aliases_link_pdf_and_object_image`) is `skipUnless` `dataset/` exists.
- Timing and linkage: lines 48, 80, 114, 119. Worker seconds resolve account and policy without a state claim. Checkpoint precedes later linked follow-up. Earliest-activity tiebreak. Corrected support and restore centers (49.5 and 50.5).
- Audit cutoff and state: lines 127, 149, 135. Future-only search does not enter the plan. Replica survivor and future absence (primary NOT_FOUND vs replica ACTIVE). Absent analytics verifies absence.
- Identity and tombstones: lines 140, 163. Historical email hash is a subject token. Tombstone requires redaction of direct email (`REPORT_EXPOSED_PII`, `REDACT_RECORD`, `VERIFY_RECORD_REDACTED`).
- Classification and citation: lines 171, 176, 185. Negated request is not deletion. Future citation rejected by `validate`. A shared report time cannot assign one account to two cases.

### tests/test_submission.py: 20 test functions (25 collected cases with parametrization)

Functions at lines 31, 40, 48, 56, 64, 76, 92, 98, 104, 109, 116, 129, 141, 151, 163, 169, 181, 194, 205, 216. Parametrized: `test_custom_case` (5 names, lines 29-30) and `test_lookup_cache_miss_does_not_override_resource_readback` (2 cases, lines 72-75). Two fixtures are used: `tmp_path` and `monkeypatch`. `needs_dataset` (line 25) marks only `test_pdf_parser` (line 91). No LLM mock. Everything runs through `predict(..., sample=True, offline=True)`.
- Parser checks: lines 40, 48, 56, 64, 92, 98, 104. JSON, SQL, log, text, PDF (skipped without dataset), image, and OCR skipped when the executable is missing.
- Injection and malformed input: lines 109, 116, 129, 141. Screen text is data. Request instruction does not change policy (byte-identical plan). Malformed sources warn and keep coverage. Malformed log lines warn.
- Readback vs cache: lines 72-88. A log cache miss does not override a resource readback.
- Identity: line 151. Old email, uppercase input, email hash, and phone digits all resolve to `user_1`.
- Custom case end-to-end: lines 29-37 (exact `rows == [expected]`), 163-166 (`after_audit` COMPLETE, cites only `evidence_01`), 169-178 (anonymous analytics linked by timing).
- Ordering and validation: lines 181-191 (canonical order FINDING, REMEDIATION, VERIFICATION, then resource ID), 194-202 (validator rejects blank citation and wrong `step_no`, error text "citation presence" and "schema/number").
- Secrets: lines 205-213. `_key()` reads `OPENAI_API_KEY` only and raises `RuntimeError` if missing. It also deletes the fallback names `OPEN_AI_API` and `open_ai_key`.
- Worker operation: lines 216-233. A failed `DELETE_RECORD` selects the category `SUPPORT_ATTACHMENT` without proving state. `REDACT_RECORD` maps to `SUPPORT_MESSAGE`. Analytics maps to `MARKETING_PROFILE`.

## Submission checks (what test_submission.py enforces)

- Enforced: custom case outputs exactly equal `sample_output.csv` (lines 29-37). Canonical step order and sorting (181-191). Citation presence and schema/number through `validate` (194-202). Future citation rejected (in test_ghost:176). Audit cutoff (163-166). `OPENAI_API_KEY` read from environment only (205-213).
- Not enforced by any test I read in `tests/` or `ghost/`:
  - `output.csv` existence, its 518-row count, header `case_id,deletion_status,steps_json`, or sort by `case_id`. The only `output.csv` references are in `ghost/validate.py:93` (CLI default path) and `main.py:196`.
  - `evaluation/evaluation_report.md` or `evaluation/usage_report.md` (grep for both returned no hits in `tests/`, `ghost/`, `main.py`).
  - Five-row minimum for custom cases beyond the five folders.
  - README run instructions.
- The one check that touches the full set is the `serve`/audit HTTP test (test_agent.py:456), which uses `case_533` and only runs with `dataset/` present.

## Missing artifacts (report files, log, output present or not)

Searched the whole repo excluding `.git` for `evaluation_report.md`, `usage_report.md`, `output.csv`, `log.txt`. None found.

- `evaluation/evaluation_report.md`: missing.
- `evaluation/usage_report.md`: missing.
- `output.csv` (repo root): missing.
- `log.txt`: missing.
- `dataset/`: missing. Dataset-dependent tests skip: `test_ghost.py:38`, `test_submission.py:91-92`, `test_agent.py:456`. Running `evaluation/main.py` with default `--dataset dataset` would fail.
- `runs/`: missing.
- Present: `.env.example`, `.gitignore`, `LICENSE`, `README.md` (22041 bytes), `docs/`, `ghost/`, `main.py` (10991 bytes), `pyproject.toml`, `requirements.txt`, `.github/workflows/tests.yml`.

## Git history shape

- `git log --oneline | wc -l` = 7 commits. `git log --oneline | head -50` shows all 7.
- Date range: all commits are on 2026-10-31. Timestamps run 00:34:30 to 01:08:31 (+0530), a span of about 34 minutes.
- Author: single author, "G26Karthik" (all 7).
- Commit list, oldest first:
  1. c5f49f5 Add deterministic audit engine: evidence, identity, timing, state and policy (00:34:30)
  2. 95fdaea Add tool-using agent loop, submission gate and CLI (00:34:30)
  3. 9cca2e9 Add tests, scoring scripts and synthetic evaluation cases (00:34:31)
  4. 1db148a Add README, architecture and results docs, CI (00:34:32)
  5. 79c24ec Add view-only license and approach write-up (00:54:16)
  6. e4642ca Fold docs into a single README with stage diagrams and visuals (01:04:27)
  7. c9823c3 Remove internal workflow markers from source comments (01:08:31)
- Style: imperative, sentence case, no type prefixes, no trailing period, mostly "Add ..." (5 of 7 start with "Add"). Subjects are descriptive and list components.
- Shape observations: commits 1 to 4 are within about 2 seconds, so they were likely batch-created or rebased rather than made incrementally. Commit 7 removes "internal workflow markers" from source comments, which is a cleanup of process traces. Only commit 3 mentions scoring scripts, and the scoring logic lives in `evaluation/main.py`.

## Notable/differentiating ideas

- Deterministic oracle with a gate: the model proposes a plan, and `AgentTools.canonical_plan` recomputes it from facts. The gate diffs the proposal against the canonical row and rejects unseen resources, unseen categories, future citations, and changed evidence IDs (test_agent.py:144-167, 170-185). Hallucinated resources fall back to the deterministic row after 3 rejections (test_agent.py:208-217). This makes the LLM a proposer rather than the authority.
- Audit cutoff enforced at several layers: validator, resource derivation, and citation. The custom case `after_audit` is the regression case (test_submission.py:163-166).
- Prompt-injection defense is tested explicitly: injected instructions in source text (test_agent.py:231-240), hostile request text yields the same plan (test_submission.py:116-126), and malicious screen text is data (test_submission.py:109-113).
- Replay and cost control: JSONL call cache with tail-corruption tolerance, deterministic offline replay with zero fresh calls (test_agent.py:418-451), budget gate before the provider call, a circuit breaker after 3 transport errors, and a usage receipt written even for incomplete responses.
- Pinned SDK wire-format test with `httpx2.MockTransport` (test_agent.py:306-326) catches request-shape drift in `openai==3.37.0`.
- Weaknesses relevant to the required reports:
  - `evaluation/main.py` prints metrics but does not persist them, so `evaluation_report.md` must be hand-written.
  - `score()` uses positional zip for field accuracy, which hides missing and extra steps in field accuracy (the step-level numbers do catch them).
  - Duplicate `case_id` rows are not detected.
  - `timing_diagnostic.py` depends on hardcoded constants (40 to 80 minutes, 51 to 52 seconds, and `POLICY_OFFSETS`) and a hardcoded `runs/final` directory.
  - No test enforces the 518-row `output.csv` contract.
- Custom cases map one-to-one to the failure modes in the README and to specific tests, which is a good audit trail. Each folder is a single request, though, so they test scenario logic, not throughput or scale.
