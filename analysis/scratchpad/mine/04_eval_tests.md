# 04 Evaluation, tests, usage, and log audit (read-only)

## Evaluation harness (metrics computed, how scored, CLI)

- Entry point: `code/evaluation/main.py`. Run with `python code/evaluation/main.py`, or `make eval` (Makefile:20-21, which calls it). It always exits 0 and never gates (main.py:4, 210).
- Scored set: the 32 public samples (`dataset/sample_deletion_requests.csv` against `dataset/sample_output.csv`), plus 3 custom cases in `code/evaluation/cases/`. The 518 evaluation requests are never scored (main.py:184 for samples, main.py:164 for custom; report heading at evaluation_report.md:5 says the same).
- The pipeline runs as a subprocess, `code/main.py --requests ... --output ...` (main.py:114-118). Samples run twice (main.py:182-183) for the determinism check.
- Metrics (main.py:39-67, 101-105, 82-98):
  - `status`: share of cases whose `deletion_status` matches.
  - `step`: share of expected steps that match on all 7 fields, position by position (main.py:49-57). Extra or missing steps count against the total.
  - `field`: share of the 7 `FIELDS` (step_no, phase, system_id, resource_id, operation, state, evidence_id) matching position by position. Missing or extra steps add to the denominator with zero credit (main.py:52).
  - `sequence`: share of cases whose ordered tuple `(phase, operation, system_id, resource_id)` matches exactly (main.py:58-60). `state` and `evidence_id` are not part of this key.
  - `citation`: share of non-empty `evidence_id`s that exist in `evidence_files.csv`, `system_activity.csv` or `user_audit_log.csv`, and whose timestamp is <= the case's `audit_at` (main.py:70-98).
  - `determinism`: 100 if the two sample runs have byte-identical `(deletion_status, steps_json)` (main.py:101-105).
- Headline = 0.25 status + 0.20 step + 0.15 field + 0.20 sequence + 0.10 citation + 0.10 determinism (main.py:21, 108-109).
- Custom-case pass rule: status == 100 AND sequence == 100 for that case (main.py:173-174). `citation` and `determinism` are not checked per custom case.
- Report writer: `render_report` (main.py:131-156) overwrites `evaluation/evaluation_report.md`. The score-history table is rebuilt from the existing file, and the "Failures" section is carried over verbatim (main.py:195-204).
- Other CLIs: `code/usage_report.py` (writes `evaluation/usage_report.md`, `make usage`); `code/validate_output.py` (`make validate`); `code/package.py` (`make package`). Only the CLIs above are relevant to scoring.
- Caveat on determinism: LLM responses are cached on disk by `cache_key(model, prompt, payload)` (code/llm.py:30, 92-101). Two sample runs therefore mostly replay the same cache entries, so the 100.00 determinism score (evaluation_report.md:14) does not prove that the model is deterministic. It only shows that the cache replays.
- Caveat on overfitting: the failure log (evaluation_report.md:61-75) describes per-case fixes (case_03, case_04, case_05, case_15, case_17, case_18, case_21-case_23, case_25, case_31). They were all tuned against the same 32 samples that the score is computed on. Those scores are a development fit, not held-out accuracy.

## Custom cases (table: case | scenario | expected status | trap guarded)

Source: `code/evaluation/cases/requests.csv` (lines 2-4), `expected.csv` (lines 2-4), `notes.csv` (lines 2-4).

| case | scenario | expected status | trap guarded |
| --- | --- | --- | --- |
| custom_01 | Access/export request ("send me a copy ... I do not want anything deleted"), reported COMPLETE | NOT_APPLICABLE, `[]` | Non-deletion request must not be treated as a deletion case. Depends on the LLM intent gate. |
| custom_02 | Erasure request sent from a historical email in upper case (`MINJUN.KIM90@gmail.com`); the request says the old address was used at sign-up | INCOMPLETE, 5 steps (analytics_9914 REPORT_REMAINING_RECORD PRESENT, then DELETE_RECORD and VERIFY_RECORD_ABSENT; account_9797 VERIFY_RECORD_ABSENT; audit_record_2945 VERIFY_RECORD_PRESENT) | Historical-identifier resolution and case-insensitive email matching. |
| custom_03 | Spanish erasure request, PARTIALLY_COMPLETE; the account tombstone still holds direct identifiers | INCOMPLETE, 5 steps (tombstone_9178 REPORT_EXPOSED_PII, REDACT_RECORD, VERIFY_RECORD_REDACTED) | Multilingual intent detection. Tombstone must get REDACT, not DELETE. Expected output keeps `tombstone_9178` and does not delete it. |

Expected-step structure is in `code/evaluation/cases/expected.csv`. Only `custom_01` is NOT_APPLICABLE, and it is the only one that tests the intent gate.

## Reported scores (quote exact numbers from evaluation_report.md: case accuracy, step, field, sequence)

From `evaluation/evaluation_report.md`, latest row (`run`, line 55):

- Case-level deletion-status accuracy: **100.00** (line 9)
- Step-level accuracy: **96.89** (line 10)
- Field-level accuracy: **97.78** (line 11)
- Sequence accuracy: **93.75** (line 12)
- Citation validity (32 samples): **100.00** (line 13)
- Determinism: **100.00** (line 14)
- Headline: **97.80** (line 15)
- Custom cases (lines 31-34): status 100.00, step 100.00, field 100.00, sequence 100.00. Cases: 3 (line 36). Each case PASS (lines 38-40).

Arithmetic check: 0.25x100 + 0.20x96.89 + 0.15x97.78 + 0.20x93.75 + 0.10x100 + 0.10x100 = 97.795, which rounds to 97.80. Consistent.

Sequence 93.75 = 30/32. The two misses are `case_18` and `case_20`, which the report says are missing `VERIFY_RECORD_PRESENT` steps for audit records `audit_record_6645` and `audit_record_5569` (evaluation_report.md:76). Those audit records appear in no participant-visible evidence, per the report.

Score history (lines 44-55): the first row is a stub at 20.00 headline (line 46). The headline rises to 97.80 over 10 labelled runs. Rows with labels such as "intent gate skipped (offline mode, since removed)" (line 47) and "phase1 ... phase5" (lines 48-54) were scored with the offline gate skipped, per the note at line 59. The latest row is labelled "run" (line 55), with no label, and the table has no description per row.

## Usage/cost report (models, calls, tokens, cost — quote exact numbers)

From `evaluation/usage_report.md`:

- Requests in the final run: **518** (line 3)
- Provider/model: openrouter, `deepseek/deepseek-v4.1-flash` (line 7)
- Model calls: **852**; cache hits: **14781**; input tokens: **269184**; output tokens: **89580**; total tokens: **358764**; est. cost: **0.0950 USD** (lines 7-8)
- Average tokens per request: **692.6** (line 10)
- Estimated cost per request: **0.000183 USD** (line 11)
- Calls by purpose: `{'intent': 809, 'image_extraction': 43}` (line 12). 809 + 43 = 852, consistent.
- Price used: $0.02 per 1M input, $1 per 1M output, from the OpenRouter list price (line 13). Same as `code/llm.py:19`, `PRICE_PER_M = (0.02, 1.0)`.

Arithmetic check: (269184 x 0.02 + 89580 x 1.0) / 1e6 = 0.09498, which rounds to 0.0950. Average 358764 / 518 = 692.6. Both consistent.

Concern: the usage ledger is opened in append mode (code/llm.py:88-90) and `summarize()` reads the whole file (code/usage_report.py:19-33). It does not filter to the final run. The header "Requests in the final run: 518" is therefore not guaranteed to match the ledger contents. The ledger is also gitignored (`.cache/` in `.gitignore`) and is not present in this checkout (`ls .cache` fails). The usage numbers cannot be regenerated or verified from this checkout.

Only one model is used. Model is pinned in `code/llm.py:17`, `MODEL = "deepseek/deepseek-v4.1-flash"`. The `usage_report.md` values are consistent with that single model.

## Output.csv statistics

Source: `/home/user/hackerrank-orchestrate-october26/output.csv` (519 lines including header, 518 data rows). Header is exactly `case_id,deletion_status,steps_json`. Unique case IDs = 518, sorted by case_id.

- Status distribution: INCOMPLETE 347, COMPLETE 161, NOT_APPLICABLE 10.
- Average steps per status:
  - INCOMPLETE: avg 7.58 (min 3, max 14, n = 347)
  - COMPLETE: avg 3.28 (min 1, max 6, n = 161)
  - NOT_APPLICABLE: avg 0.00 (all 10 rows have `steps_json = []`; 0 NOT_APPLICABLE rows carry steps)
- Phases: FINDING 703, REMEDIATION 703, VERIFICATION 1753.
- Operations: REPORT_REMAINING_RECORD 357, REPORT_EXPOSED_PII 212, REPORT_ACTIVE_DATA_FLOW 108, REPORT_RESTORE_RISK 26, DELETE_RECORD 357, REDACT_RECORD 140, ANONYMIZE_RECORD 72, DISABLE_DATA_FLOW 108, BLOCK_RESTORE 26, VERIFY_RECORD_ABSENT 812, VERIFY_RECORD_PRESENT 374, VERIFY_RECORD_REDACTED 178, VERIFY_RECORD_ANONYMIZED 189, VERIFY_DATA_FLOW_DISABLED 142, VERIFY_RESTORE_BLOCKED 58.
- States: ABSENT 1169, PRESENT 943, REDACTED 318, ANONYMIZED 261, DISABLED 250, ACTIVE 134, BLOCKED 84.
- Internal consistency: all FINDING ops (357 + 212 + 108 + 26 = 703) pair with REMEDIATION ops (357 + 140 + 72 + 108 + 26 = 703). Each finding has a matching remediation count. Good sign for the contract, though it does not prove correctness.
- Contract points not exercised in this read: `evidence_id` on findings is non-empty, and remediation/verification use `""`. I did not check those per row.
- `code/validate_output.py` exists for the contract check. It was not run here (read-only analysis).

## Tests & CI (present or absent)

- Test suite: **absent**. No `test_*.py`, `*_test.py`, `conftest.py`, `pytest.ini`, `tox.ini`, `setup.cfg` or `pyproject.toml` outside `dataset/`. The repo's `tests/` directory was deleted by the archived OpenSpec change `openspec/changes/archive/2026-10-25-remove-dead-code/proposal.md:10` and `tasks.md:11`. `pytest` is not in `code/requirements.txt` (`pypdf`, `openrouter`, `Pillow`).
- `graphify-out/GRAPH_REPORT.md:127` still lists a `test_determinism()`, `test_headline_formula()`, `test_perfect_match_scores_100()` etc. graph. These are stale references to the deleted tests, not live tests.
- CI config: **absent**. No `.github/` directory. No `.gitlab-ci.yml`, `.circleci`, or similar found.
- Only verification is the eval harness (`make eval`), which per the archive proposal is the only verification (`openspec/changes/archive/2026-10-25-remove-dead-code/proposal.md:10`).

## log.txt stats

Measured on the file as it stood during this read. It is growing as the parent session appends.

- Size at first read: 894 lines, 37442 bytes. Size at second read: 924 lines, 38107 bytes.
- `## [` entries: 35 (at the second read).
- `SESSION START` entries: 10 (grep -c). Header lines at 145, 362, 611, 740, 885, 896, plus others.
- `model=` lines (47 total with `tool=`):
  - `model=claude-sonnet-5-5`: 27
  - `model=claude-opus-5-5`: 18
  - `model=claude-haiku-5-5`: 2
  - `model=runtime-model-not-exposed`: 2 (lines 148, 356)
- `tool=` lines:
  - `tool=Claude Code`: 47
  - `tool=github_copilot_vscode_agent`: 2 (lines 147, 355)
- Compliance concerns against AGENTS.md §5.1-5.2: `model=runtime-model-not-exposed` (line 148, 356) is a placeholder, and AGENTS.md forbids `unknown`, generic or inferred values. The `github_copilot_vscode_agent` tool name at lines 147 and 355 is a different harness label from the other 47 entries. Both are in the first session block (line 145). I did not change the log, per the read-only scope.
- Not copied prompts, as instructed.

## Failures/improvements documented

From `evaluation/evaluation_report.md:57-76`, the failure table has 13 rows (lines 63-74). Highlights:

- Partial JSON bundles treated omitted records as absent (line 63). Fix: omission counts as absence only for SQL dumps and empty bundle extracts.
- Primary-deleted but replica-held record reported absent, `case_05` (line 64). Fix: per-store state; any copy counts as present.
- Name-less trace keys missed, `case_15` and `case_17` (line 65).
- Later empty snapshot chosen over explicit lookup, `case_21` to `case_28` (line 66).
- Post-`audit_at` evidence leaking into state (line 67). Fix: only files captured at or before `audit_at`.
- Accounts and anonymized analytics unlinkable (line 68). Fix: `ActivityLinker` heuristics on timing slots, regular gaps, and elimination. This is a heuristic linker, which is fragile on unseen data.
- PDF attachments and legacy contact-index records misclassified (`case_07`, `case_10`, line 69).
- `case_03` wrong analytics event (line 70). Fix: chain-gap scoring tuned to 390 s and 449 s, the gaps seen in the samples. This is an overfit constant.
- `case_04` account id (line 71). Fix: account ids mirror the user number (`account_004` for `user_04`), an assumption that is tuned to the sample naming.
- `case_17` stale lookup (line 72).
- `case_21` to `case_23` account result tracked to reported status, with COMPLETE->SUCCESS, NOT_STARTED->FAILED, PARTIALLY_COMPLETE->PARTIAL/SUCCESS, "79 mismatches across 518 cases fell to 7" (line 73). This is a rule fitted to reported statuses across the full 518 set, which is a claim based on reported status, not evidence. Worth flagging.
- `case_21` analytics owner ambiguity (line 74).
- Known remaining (line 76): `case_18` and `case_20` miss one `VERIFY_RECORD_PRESENT` each (`audit_record_6645`, `audit_record_5569`).

Line 59 notes that rows labelled with a phase or trial were scored with the LLM intent gate skipped. Those score rows are not directly comparable to the latest run.

## Notable ideas

1. Hold-out split. The 32 samples drive all fixes (case-specific constants at evaluation_report.md:70-71, 73). Keep a few samples out of development, or make the custom cases do double duty as a held-out set. The three custom cases alone are too few.
2. Make determinism real. Run the sample set once with `--no-cache` (or a fresh cache dir) and compare; the current 100.00 (line 14) only shows cache replay. Or label the metric as "cache replay".
3. Per-run usage ledger. Stamp each ledger line with a run ID (or truncate at the start of each run), so `usage_report.md` really reports the final full-dataset run. Today it sums the whole append-only file (code/usage_report.py:19-33; code/llm.py:88-90).
4. Ledger in the repo. `.cache/` is gitignored, so the usage numbers cannot be reproduced from a clean checkout. Either commit a summary JSON for the final run, or write a snapshot into `evaluation/`.
5. Sequence metric blind spot. `sequence` ignores `state` and `evidence_id` (main.py:58). A wrong state (e.g., ABSENT vs REDACTED) with correct ops still scores as sequence-correct. Adding state to the key would tighten the metric.
6. Field metric denominator. Missing or extra steps add 7 zero-credit fields each (main.py:52), so length errors are double-penalised across step and field. This is fine but should be documented.
7. Restore the test suite. Zero tests remain. Cheap candidates: a unit test for `citation_validity` (cutoff logic), `score_outputs` (length mismatch), `history_rows` (re-append rule), and the CSV contract (518 rows, sorted, valid JSON, step_no sequence, phase order).
8. Log hygiene. Two entries use `model=runtime-model-not-exposed` and two use `tool=github_copilot_vscode_agent`, which AGENTS.md §5 forbids. Fix going forward (the log is append-only, so note the correction in a new entry rather than editing old ones).
9. Score-history labels. The latest row is labelled only "run" (evaluation_report.md:55). Labels would make the history auditable (e.g., git commit hash plus run timestamp).
10. Stale graph. `graphify-out/GRAPH_REPORT.md:127` still lists deleted test functions. Refresh with `graphify update .`, as AGENTS.md §10 says.

Scope note: I did not run the pipeline, did not modify any project file, and did not append to `log.txt` (the read-only instruction overrides AGENTS.md §5 logging for this subagent turn). The only file written is this one.
