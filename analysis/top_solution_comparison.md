# Ghost Data Still Exists: Your Solution vs the #1 Ranked Solution

Compared repositories:

- **Yours:** `Vijay431/hackerrank-orchestrate-october26`, at the state of branch `ccr-6d96f2a2-5bdrvk`.
- **#1:** `G26karthik/ghost-data-still-exists`, at HEAD `c9823c3`. Its README says it placed 1st of 4,650.

Method: eight Haiku subagents read the two codebases without running them. There were four agents per repo, each covering one area: meta and dependencies, LLM pipeline, domain logic, and evaluation and tests. Each agent wrote to a scratchpad under `analysis/scratchpad/{top,mine}/`. The orchestrating agent then checked the claims that drive the conclusions directly against the source; those are marked **[verified]**. Every other claim comes from the scratchpads, which hold the file:line references.

> The #1 repo's LICENSE is "view-only, all rights reserved". Use it to learn ideas. Do not copy code from it.

---

## 0. TL;DR: what actually separated #1 from you

1. **Neither solution's answers come from the LLM.** In both repos, deterministic code produces every row. The #1 repo even decides authorization with keywords: `intake.py:56` always keeps the regex result from `is_deletion_request` **[verified]**. The model's answer is only logged as a "disagreement". So the rank was not won by "more AI".
2. **The #1 repo turned a hidden data signal into an engine, and then validated it on the full set.** It noticed that the dataset's deletion worker performs policy actions at fixed second-of-minute offsets from the account delete (+19.5 s, +20.5 s, +49.5 s, +50.5 s, follow-up +51.5 s) **[verified, `ghost/activity.py:30-44`]**. It built a one-to-one, fixed-point assignment on top of that, with explicit tie handling. It then measured the hypothesis on **224 independently linked evaluation cases** (`evaluation/timing_diagnostic.py`) instead of tuning against the 32 samples. Your `ActivityLinker` uses the same idea in a weaker form: chain gaps fitted to "390 s and 449 s", a 41 s first-action offset, and zip-pairing. It was tuned case by case on the samples.
3. **On the public samples you are roughly tied.**

   | | #1 | You |
   |---|---|---|
   | Statuses correct | 32/32 | 32/32 |
   | Exact rows | 29/32 | ~30/32 sequence-correct |
   | Steps | 190/193 (multiset) | 96.89% (positional) |

   The gap is on the **hidden 518** and in the **non-score parts of the submission**: interview story, engineering rigor, documentation.
4. **The #1 repo is engineered like a product. Yours is engineered like a script.**

   | | #1 | You |
   |---|---|---|
   | Tests | 63 | 0 (deleted on 10-25) |
   | CI | GitHub Actions | none |
   | Dependencies | pinned `==` | unpinned |
   | Output | atomic writes | — |
   | Failure handling | budget cap, circuit breaker, offline replay | — |
   | Prompt-injection tests | yes | — |
   | Custom eval cases | 5 runnable mini-datasets | 3 rows in a CSV |

5. **The #1 README tells a story a judge can grade.** It has "What failed first" with numbers (0/24 → 18/32 → 29/32 → 503/518), Mermaid diagrams, honest caveats ("29/32 is a fit, not a holdout"), and explicit safety bounds. Your README is a setup manual and contains no results.
6. **The LLM is used for a defensible role.** The #1 repo wraps the deterministic engine in a **tool-calling agent plus a gate**. The model investigates through 8 read-only tools and proposes a plan. A gate diffs it against the private canonical plan, and anti-hallucination sets reject any resource or citation the tools never returned. Agreement on first submission was 503/518, with 0 fallbacks. This doesn't change the CSV, but it is a strong answer to "where is the AI agent?" in the AI interview. Your answer is "a yes/no intent call and screenshot OCR".

---

## 1. Scoreboard (self-reported, not hidden-set accuracy)

| Metric | #1 (README) | You (`evaluation/evaluation_report.md`) |
|---|---|---|
| Hidden-set rank | 1st / 4,650 | — |
| Output: INCOMPLETE / COMPLETE / NOT_APPLICABLE | **355 / 153 / 10** | **347 / 161 / 10** |
| Public samples: statuses | 32/32 | 100.00 |
| Public samples: exact rows | 29/32 | not reported (sequence 30/32) |
| Public samples: steps | 190/193 multiset, none extra | step-level 96.89 positional |
| Model | `gpt-6-luna` (OpenAI Responses API, low reasoning) | `deepseek/deepseek-v4.1-flash` (OpenRouter, temperature 0) |
| Fresh model calls | 5,190 (5,211 incl. probes) | 852 (809 intent + 43 image) |
| Tokens (in / out) | 13,734,621 / 354,814 | 269,184 / 89,580 |
| Cost | USD 0.4747 (~0.001 / request) | USD 0.0950 (~0.00018 / request) |
| Wall time | 1,181 s, 8 workers | not reported |
| Tests | 63 (14 + 25 + 24) | 0 |

**Reading the status split:** #1 says INCOMPLETE on 8 more cases than you do, and COMPLETE on 8 fewer. The likely cause is its timing correlation: it attributes more anonymous records (analytics, support, tombstone, flow, backup) to a subject. That surfaces findings your linker misses, so those cases come out COMPLETE in your output. This is the single most probable driver of the hidden-set gap. It cannot be proven without the hidden labels.

---

## 2. Folder architecture, side by side

```
#1  ghost-data-still-exists/                    YOU  hackerrank-orchestrate-october26/
├── main.py            CLI: batch|audit|serve   ├── code/main.py        CLI: --requests --output
├── ghost/             engine package (13 f)    ├── code/               flat modules (17 .py)
│   ├── identity.py    67  token index          │   ├── identity.py     87
│   ├── evidence.py   437  all parsers          │   ├── ingest.py      456  all parsers
│   ├── activity.py   236  worker timing ★      │   ├── state.py       373  facts+linker+state
│   ├── state.py      237  state @ audit_at     │   │                       (linker mixed in)
│   ├── policy.py      77  rule → treatment     │   ├── policy.py       67
│   ├── planner.py     84  canonical plan       │   ├── planner.py     152
│   ├── validate.py   116  contract + citations │   ├── validate_output.py 82 (not called by main)
│   ├── intake.py      57  batched intent       │   ├── intent.py       40  per-case intent
│   ├── vision.py      53  LLM screenshot read  │   ├── vision.py       82  Pillow tiling + LLM
│   ├── llm.py         99  cached client        │   ├── llm.py         119  OpenRouter + cache
│   ├── agent.py      422  tool loop ★          │   ├── loader.py / paths.py / progress.py
│   └── agent_tools.py 378 8 tools + gate ★     │   ├── prompt_registry.py + prompts/*/vN.txt ★
├── evaluation/                                 │   ├── usage_report.py / package.py ★
│   ├── main.py        scorer (P/R/F1)          │   └── evaluation/main.py + cases/*.csv (3)
│   ├── timing_diagnostic.py ★                  ├── evaluation/*.md     generated reports ★
│   └── custom_cases/ 5 full mini-datasets ★    ├── openspec/  spec-driven change history
├── tests/  test_ghost / test_submission /      ├── .claude/   9 opsx commands + 9 skills
│           test_agent (63 tests) ★             ├── graphify-out/  code graph (stale)
├── .github/workflows/tests.yml ★               ├── Makefile  install/run/eval/usage/package
├── docs/assets/  hero/cutoff/timing SVG ★      ├── AGENTS.md / CLAUDE.md / log.txt
├── pyproject.toml (pytest cfg only)            ├── output.csv (committed)
└── requirements.txt (pinned)                   └── code/requirements.txt (unpinned)
```
★ = notable strength.

Structural takeaways:

- **#1 has one module per pipeline stage, and timing gets its own module (`activity.py`).** In your repo, the linker heuristics sit inside `state.py`, which makes them harder to test and harder to explain.
- **#1 keeps evaluation inputs as complete mini-datasets** with the same schema as `dataset/`. Its pipeline runs on them unchanged (`--dataset evaluation/custom_cases/x`). Your custom cases are rows that point into the real dataset.
- **You are ahead on process artefacts:** versioned prompts, `package.py` with an exclusion post-check, generated eval and usage reports, OpenSpec history, and a Makefile. #1 has no generated `evaluation_report.md` or `usage_report.md` in the repo; its README says they shipped only in the submission zip.

---

## 3. Dependencies & versions

| Concern | #1 | You |
|---|---|---|
| Python | 3.11 (CI-pinned; README says "3.11 or newer") | "3.10+" (README only) |
| Build | `pyproject.toml` (pytest config only), no `[project]` | none |
| LLM SDK | `openai==3.37.0` | `openrouter` (unpinned) |
| PDF | `pypdf==6.10.0` | `pypdf` (unpinned) |
| Images | none (base64 straight to the model) | `Pillow` (unpinned), for tiling and upscaling |
| Test | `pytest==8.3.4`, `httpx2==2.16.0` (wire-format mock) | — |
| OCR | optional Tesseract cross-check (`--ocr-crosscheck`) | — |
| Stdlib | sqlite3 (sandboxed with an authorizer), csv, json, concurrent.futures, http.server | sqlite3 (no authorizer), csv, json, concurrent.futures, zipfile |
| Lock / hashes | none | none |
| CI | Actions: checkout@v4, setup-python@v5 (pip cache), `pytest -q` | none |

**Lesson:** pin every dependency with `==`. A judge or reviewer who installs a month later should get the same SDK. Unpinned `openrouter` is the biggest reproducibility risk you have.

---

## 4. LLM strategy

| Dimension | #1 | You |
|---|---|---|
| Who writes the CSV row | Deterministic `plan()`. An accepted agent submission returns the **canonical** row (`agent_tools.py:377-378`). | Deterministic `build_steps()` |
| Intent | Batched (25 per call), strict JSON schema with `authorizes_deletion`, `request_type` enum, and a verbatim `evidence_phrase`. The **regex guard always wins** **[verified]**; the LLM only flags disagreements. | One call per case. Free-text JSON recovered by regex. **LLM is authoritative**, with no fallback. |
| Multilingual | Prompt names EN/ES/PT/FR/JA/KO with examples; regex has `borr`, `supprim`, `löschen`, `削除`, `삭제`, `exclusão` … | Fully delegated to the model ("any language") |
| Follow-up "verify my deletion" requests | Covered by `gone`, `privacy request` keywords | Explicitly covered in prompt v2 ✔ |
| Vision | One call per PNG, `detail: high`, strict nullable schema of 22 fields, "Do not state a deletion verdict" | Pillow crops 3 bands + panel, upscales, transcribes plain text, then regex parse ✔ (clever for small models) |
| Agent loop | Responses API, `tool_choice=required`, no parallel calls, 24 tool cap (26 when flagged), up to 3 submissions, strict schemas | none |
| Anti-hallucination | Every resource, evidence ID and category in a proposal must have been returned by a tool in that case | n/a |
| Prompt-injection hardening | "untrusted data" in every prompt, plus 3 tests | Fenced `<request_text>` in prompt v2 ✔, no tests |
| Structured output | `json_schema`, `strict: true` everywhere | none (regex `{...}`) |
| Cache | SHA-256 of the full payload; JSONL with truncated-tail tolerance; replay checks model and effort | SHA-256 of (model, prompt, payload) ✔. **Raw text is cached before parsing**, so a bad answer is replayed forever. |
| Retries | Own loop, 3 attempts, 408/409/429/5xx only, honours `retry-after` | 4 attempts on any exception, including 400s |
| Cost guard | Hard USD budget reserved before each call, circuit breaker after 3 errors | none |
| Offline | `--offline` degrades the agent to deterministic output | Works only with a warm `.cache/`, which is gitignored and not packaged |

**Interpretation.** #1's model choice (a more expensive model, 5× your cost) bought **no accuracy**, because the gate forces the canonical row. What it bought is a credible "agentic" architecture, safety guarantees, and a story. Your cost efficiency (USD 0.095) is genuinely better. Your weakness is that the LLM is a single point of failure for intent, and there is no deterministic guard when it is wrong.

---

## 5. Domain logic, stage by stage

| Stage | #1 | You | Edge |
|---|---|---|---|
| **Identity** | Token set: user_id, emails, SHA-256 of **every historical email**, phone digits (9–15). Collision means hard fail. | user_id, emails, phones, hashes from audit log old and new values. First wins on collisions. | #1 (hashes historical emails, fails loudly) |
| **Linking window** | Evidence must be captured in `[requested_at − 30d, audit_at + 7d]` to link | Link by `observed_at ≤ audit_at` only; `owners_map` has no time cutoff | #1 |
| **Anonymous-record attribution** ★ | `activity.py`: candidate account deletes in `[report−2h, report+15m]`, narrowed to `[report−80m, report−40m]`. Fixed-point loop, fewest candidates first: identity match → timing constraints within ±0.75 s → follow-up +51.5 s → same-evidence score. A global **one-to-one** assignment across samples + evaluation, so no action is claimed twice. Explicit `earliest_activity_tiebreak`, flagged as ambiguous. Validated by `timing_diagnostic.py`. | `ActivityLinker`: 41 s first-action offset, chain gaps fitted to 390/449 s, zip-pairing when counts are equal (arbitrary), the `user_NN → account_NNN` naming convention, and a reported-status → result mapping fitted on the 518 set. | **#1, decisively** |
| **Claims vs state** | Activity is used only for ownership and timing. State comes only from readbacks. `reported_status` is only a preference filter. | Same principle ✔ | tie |
| **SQL** | In-memory sqlite with an **authorizer** (no ATTACH, only `json_valid`). Tables with `replica` or `primary` in the name are kept as **separate physical copies**. | In-memory sqlite, no authorizer. Table-level `store` computed (`ingest.py:175`) but **never used**: `state.py:127/134` keys by file stem **[verified]**, so primary and replica in one dump share one slot, and the first one offered wins ties. | #1 |
| **Replica drift rule** | Latest per physical copy, then any surviving non-ABSENT copy dominates | Any present store dominates ✔ (but see the bug above) | #1 |
| **Logs** | 5 envelope formats (JSON, k=v via `shlex`, pipe, bracket, `<…>`); 13 subject-key names; malformed lines warn | 3 formats (JSON, cloud `message=`, RFC5424) | #1 |
| **PDF** | pypdf; whole-document context when exactly one resource is named; alias linking through `LINK_RESOURCE_IDENTITY` details | pypdf; regex facts; document-level refs attached to every resource (coarse) | #1 |
| **State derivation** | 11-step precedence (404/NOT_FOUND, `profile: null`, `rows=0`, empty `index_queries`, explicit result, flow keys, backup deny/block/eligible/listed image, export unavailable, account DELETED, identifiers present or absent) | `derive_state` → defaults to FOUND | #1 (richer) |
| **Policy** | Hard-coded `RULE_ACTION` **cross-checked against the CSV, fails on drift**. `condition` ignored. | Dict lookup; `condition` ignored; BACKUP always BLOCK (overrides rule_14 RETAIN); missing category is dropped silently | #1 (fail-loud) |
| **Tombstone** | REDACT group; `has_direct_identifiers` checks name / email / phone / hash fields not equal to `[REDACTED]` | REDACT with `direct_only`; **names never checked** | #1 |
| **Ordering** | Global RANK: FINDING → DISABLE → BLOCK → DELETE → REDACT → ANONYMIZE → VERIFY, then system, then resource. No downstream-before-source. | Same scheme, same gap | tie |
| **Unresolved resources** | Become gaps. INCOMPLETE adds a conditional future VERIFICATION. Late-only evidence dropped except for retained categories. | Silently dropped | #1 |
| **Validation** | `validate.py` runs **inside the pipeline**: canonical order, citation exists and is ≤ `audit_at`, state matches the operation | Standalone, never called by `main.py`; no citation-time check | #1 |
| **Fail-safety** | Unresolved identity → runtime **raises** rather than plan deletions | Unresolved email → NOT_APPLICABLE | #1 (safer story) |

★ This is the stage most likely to explain the hidden-set gap.

---

## 6. The decisive differentiators (ranked by likely impact)

1. **Generalizing the generator's worker timing into a global one-to-one assignment, validated on the full eval set.**
   - #1 picked one hypothesis ("worker actions happen at fixed second offsets after the account delete"). It wrote it down as constants, built `timing_diagnostic.py` to check it on the 224 cases where ownership is independently provable, and reported the hit rate: 224/224 for the window, and 148/151 for follow-ups after a fix from 97/142.
   - Your linker reached its sample score through case-specific patches: `case_03` gaps, `case_04` account naming, `case_21-23` status mapping. Those patches fit the 32 samples but generalize worse.
   - **Lesson:** when you find a signal, *measure it on the unlabeled 518 using an independent ground signal*, not on the 32 labels.
2. **Breadth of evidence parsing.** #1 has 5 log envelopes, 13 subject-key names, alias linking via `LINK_RESOURCE_IDENTITY` for PDFs and screenshots, empty `index_queries` as ABSENT, `profile: null` as ABSENT, and `rows=0`. Each of these adds hidden-set recall.
3. **Correct physical-copy (replica) separation** in SQL dumps. You have the code for it at `ingest.py:175`, but it is never wired in.
4. **Fail-loud invariants**: the policy-table tamper check, identity collision as an error, the validator inside the pipeline, and coverage per evidence file printed so that a parser returning zero is visible. Your solution fails silently: dropped categories, skipped images, and an unresolved email treated as NOT_APPLICABLE.
5. **Submission narrative**: the README in §8 below, plus an agent and gate design that answers the interview's "explain your architecture" with a clear trust model: *"Neither side is trusted alone."*

---

## 7. Where you were ahead (keep these)

- **Cost:** USD 0.095 total, 5× cheaper than #1, at a comparable sample score.
- **Image pipeline:** tiling and upscaling for a small model is a thoughtful engineering move.
- **Versioned prompt registry** (`prompts/intent/v1|v2.txt`), where the prompt version is part of the cache key.
- **Intent prompt v2 explicitly handles follow-up requests** ("already deleted … please verify"). #1 relies on a keyword (`gone`).
- **Generated reports.** `code/evaluation/main.py` writes `evaluation_report.md` with history, citation validity and determinism. `usage_report.py` builds the usage report from a ledger. #1's scorer only prints to stdout.
- **`package.py`** with a forbidden-path post-check.
- **Spec-driven process** (OpenSpec) and a complete `log.txt`. #1 gitignores `log.txt` and commits no process trail: 7 commits in 34 minutes, squashed.

---

## 8. Evaluation, tests, CI, docs

| | #1 | You |
|---|---|---|
| Scorer metrics | status, exact rows, step P/R/F1 (multiset), sequence, per-field accuracy, mismatch causes | status, positional step, field, sequence, citation validity, determinism, weighted headline |
| Custom cases | **5 runnable mini-datasets**: `after_audit`, `historical_replica`, `non_deletion`, `timed_analytics`, `tombstone_pii` | 3 CSV rows: access-only, historical email, Spanish tombstone |
| Hypothesis diagnostics | `timing_diagnostic.py` over all 518 | none |
| Unit tests | 63: parsers, cutoff, timing, replicas, tombstones, gate, hallucination rejection, injection, budget, breaker, cache replay, HTTP, secrets | 0 |
| CI | Actions on every push and PR | none |
| README | 305 lines: hero SVG, badges, 4 Mermaid diagrams, timing and cutoff SVGs, "What it returns", staged design, **Measured results**, **What failed first** (table with numbers), **Bounded by design**, tests table, limitations, "what isn't here" | 216 lines: setup, dataset map, contract, packaging, architecture table. **No results, no diagrams, no failure story.** Also internally inconsistent about where the eval reports go (README lines 91-99 vs 181). |
| Honesty markers | "29/32 is a fit, not a holdout"; lists the 29 tie-break-dependent IDs; "not an invoice" | Determinism = 100 only proves cache replay; score-history rows not labelled |

---

## 9. Concrete defects in your repo found during this review (fix list)

Ordered by likely score impact.

1. **Replica store collapse.** `Fact.store` (`ingest.py:175`) is ignored; `observe` uses the file-level `info.store` (`state.py:127,134`). Primary and replica tables in one dump compete for one slot. **[verified]**
2. **No `audit_at` cutoff in identity history or ownership.** `identity.py:51-58` ignores `event_time`; `owners_map` (`state.py:364-373`) and the account pass (`state.py:307-313`) have no time filter; `planner.py:79` can cite `activity_ids[0]` after `audit_at`.
3. **The LLM is the only intent authority, and its cache can be poisoned.** `llm.py:114-117` caches before `intent.parse_decision` runs, so one malformed answer crashes every rerun. Add a deterministic guard, as #1 does, and cache only after a successful parse.
4. **Names are never checked as exposure** (`planner.py:54-62`). A tombstone or support record that still holds the name is treated as compliant.
5. **Silent drops.** Unknown categories (`planner.py:122`), skipped images (`ingest.py:400-402`), and an unresolved email returning NOT_APPLICABLE (`main.py:54-57`).
6. **Substring catalog matching** (`state.py:91`): `user_1` matches inside `user_12`.
7. **Equal-count zip pairing** (`state.py:279-291`) assigns events by string order of case_id.
8. `validate_output.py` is never run by `main.py`, and does not check citation time or that findings are non-empty.
9. Unpinned dependencies; no tests; no CI; the README contradicts itself on where the eval reports go.
10. Log hygiene: 2 entries with `model=runtime-model-not-exposed` and 2 with `tool=github_copilot_vscode_agent` violate AGENTS.md §5.

---

## 10. Playbook: how to take #1 next time

**Day 0–1: understand the generator, not just the spec**

- [ ] Build a throwaway notebook that profiles `system_activity.csv`: event types × systems × second-of-minute histograms × offsets from the nearest account delete. Fixed offsets, windows and batch structure are *participant-visible evidence*. Find them first.
- [ ] For every hypothesis, write a **diagnostic over the unlabeled eval set** that uses an independent ground signal (cases where ownership is token-linked). Report the hit rate in the README.
- [ ] Inventory every evidence format and every envelope variant: grep the distinct log line shapes, JSON top-level keys, SQL table names and screenshot layouts. Parse all of them, and print a per-file coverage table so that zero coverage is visible.

**Architecture**

- [ ] Deterministic engine = source of truth. One module per stage: identity, evidence, activity, state, policy, planner, validate.
- [ ] Wrap it in an **LLM agent with read-only tools plus a gate** (proposal must equal the canonical plan; anti-hallucination sets; bounded resubmits; deterministic fallback). Cheap model, strict JSON schemas, `tool_choice=required`. This is for robustness and for the interview story, not for accuracy.
- [ ] LLM intent = cross-check; a deterministic multilingual keyword guard = authority, or the reverse with a guard on disagreement. Never let a single source decide alone.
- [ ] Fail loud: policy-table tamper check, identity collision as an error, raise on unresolved identity, validator inside the pipeline, atomic output write.
- [ ] Respect `audit_at` at **every** layer: identity history, linking window, readbacks, citations.

**Engineering hygiene (judges read code)**

- [ ] Pin every dependency with `==`. Add `pyproject.toml`, a 3-line GitHub Actions pytest workflow, and a badge.
- [ ] Write about 50 tests: one per parser, the cutoff, replicas, tombstones, ordering, the validator, prompt injection, and the cache replay.
- [ ] Make custom cases **runnable mini-datasets** (≥ 5), each guarding one named trap.
- [ ] Budget cap, circuit breaker, retry only on 408/409/429/5xx, offline replay mode.

**Submission narrative**

- [ ] README sections: Result → What it returns → How it works (staged, with diagrams) → Measured results → **What failed first** (numbers per iteration) → Bounded by design → Try it (offline demo on a custom case) → Tests → Limitations.
- [ ] State honestly what is a fit and what is held out. List the cases that depend on a tie-break.
- [ ] Keep your strengths: cost ledger, generated reports, versioned prompts, `package.py` post-check, process log.

---

## 11. Caveats

- Both analyses are static; neither repo was executed. The #1 repo ships without `dataset/`, `output.csv`, reports or caches, so its numbers are README claims.
- The hidden-set scoring formula and the weight of the AI interview are not public. "1st of 4,650" covers the whole submission, not CSV accuracy alone.
- The #1 timing constants are themselves dataset-fitted. AGENTS.md §6.7 forbids "case-family shortcuts". The difference is that #1 expressed the signal as one general, measured rule with a diagnostic and explicit tie handling, while your linker accumulated per-sample patches.
- Raw per-area findings with file:line references: `analysis/scratchpad/top/0{1..4}_*.md` and `analysis/scratchpad/mine/0{1..4}_*.md`.
