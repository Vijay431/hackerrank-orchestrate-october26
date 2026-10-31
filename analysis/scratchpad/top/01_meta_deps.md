# 01 Meta and dependencies: ghost-data-still-exists

Source repo: `/tmp/top/ghost-data-still-exists` (read-only analysis; nothing was run, installed, or modified in that repo).
Git HEAD at time of reading: `c9823c3 Remove internal workflow markers from source comments` (prior: `e4642ca`, `79c24ec`).

## Folder architecture (full tree with one-line purpose per file/folder)

```
ghost-data-still-exists/
├── .env.example                      one line: OPENAI_API_KEY= (blank, names only)
├── .gitignore                        ignores .env*, dataset/, runs/, output.csv, code.zip, log.txt, __pycache__, .venv, *.pyc
├── .github/
│   └── workflows/
│       └── tests.yml                 CI: pytest on push and PR (Ubuntu, Py 3.11)
├── LICENSE                           view-only, "All rights reserved" (not OSI open source)
├── README.md                         305-line single-file doc: result, approach, numbers, run steps, layout, limits
├── pyproject.toml                    only [tool.pytest.ini_options] (pythonpath=".", testpaths=["tests"])
├── requirements.txt                  4 pinned packages (==)
├── main.py                           CLI entry: batch run, `audit --case`, `serve` HTTP endpoint, `--offline --sample`
├── ghost/                            the engine package
│   ├── __init__.py                   docstring only: "Deterministic participant-evidence audit."
│   ├── evidence.py                   parsers for PDF (pypdf), screenshots, logs, JSON, SQL snapshots -> Observation records
│   ├── identity.py                   current + historical identifier index (emails, user_id, phone, hashes)
│   ├── activity.py                   worker-batch correlation by fixed second-offsets; tie handling
│   ├── state.py                      resource state at audit_at (captured and recorded <= cutoff)
│   ├── policy.py                     category + state -> required treatment from deletion_rules.csv
│   ├── planner.py                    builds the private "official" plan and canonical ordering
│   ├── agent.py                      Responses-API tool loop, budget, timeout, cache, AgentConfig env parsing
│   ├── agent_tools.py                the eight read-only tools plus the submission gate (diff, max 2 resubmits)
│   ├── validate.py                   CSV contract checker (header, case IDs, numbering, citations vs audit_at)
│   ├── intake.py                     batched LLM request-intent classification, keeps deterministic guard
│   ├── llm.py                        small cached Responses client; PRICES table; fixed EFFORT="low"
│   └── vision.py                     LLM transcription of visible screenshot fields
├── evaluation/
│   ├── main.py                       offline scorer: predictions vs sample_output-style answers (--dataset, --answers)
│   ├── timing_diagnostic.py          checks worker-timing offsets on requests with independently linked accounts
│   └── custom_cases/                 five synthetic mini-datasets with expected answers
│       ├── after_audit/              record created after audit_at must be ignored (has evidence/records/evidence_01,02.json)
│       ├── historical_replica/       replica still holds data at cutoff -> finding (evidence_01.json)
│       ├── non_deletion/             request is not a deletion -> NOT_APPLICABLE (evidence_01.json)
│       ├── timed_analytics/          anonymous analytics row attributed by worker timing (evidence_01.json)
│       └── tombstone_pii/            tombstone still holds name/email -> REDACT step (evidence_01.json)
│       (each case folder: deletion_requests.csv, deletion_rules.csv, evidence_files.csv,
│        sample_deletion_requests.csv, sample_output.csv, system_activity.csv,
│        user_audit_log.csv, user_identities.csv, evidence/records/*.json)
├── tests/
│   ├── test_ghost.py                 14 tests: identity, cutoff, timing offsets, replicas, tombstones, policy, classification
│   ├── test_submission.py            25 tests: every source parser, five synthetic cases, ordering, citation/numbering validation
│   └── test_agent.py                 24 tests: tool loop, gate diffs/repairs, hallucinated resources, budget, breaker, cache replay, HTTP
└── docs/
    └── assets/
        ├── hero.svg                  README banner (dark theme, 1100-ish px wide)
        ├── cutoff.svg                timeline explaining audit_at counting rule
        ├── timing.svg                60-second dial of worker action offsets
        ├── orchestrate-certificate.gif  720x490 GIF of HackerRank certificate (~4.7 MB), HackerRank's image
        └── icons/                    8 small SVG icons used as README section headers
            book.svg box.svg flask.svg flow.svg layers.svg results.svg shield.svg start.svg
```

Notes on the tree:
- Top-level `main.py` is 204 lines; `ghost/*.py` total 1,902 lines across 13 files; `tests/` total 917 lines; `evaluation/` scripts 197 lines. No `cache/` directory is present in the repo (the default path is created at runtime, see LLM section).
- `ghost/llm.py` is not in the README "Layout" block (README lines 269-287). `evaluation/timing_diagnostic.py` is not mentioned in the README at all. `ghost/__init__.py` is also omitted from the README layout.

## Dependencies & exact versions (table: package | version spec | where declared | purpose)

| package | version spec | where declared | purpose |
| --- | --- | --- | --- |
| `openai` | `==3.37.0` | `requirements.txt:1` | OpenAI Python SDK; used for the Responses API in `ghost/llm.py:13`, `ghost/agent.py:18` (README: "SDK retries are off") |
| `pypdf` | `==6.10.0` | `requirements.txt:2` | PDF text extraction, imported lazily in `ghost/evidence.py:303` (`from pypdf import PdfReader`) |
| `pytest` | `==8.3.4` | `requirements.txt:3` | Test runner; `python -m pytest` in README and CI. Test-only, but installed from the same file as runtime deps |
| `httpx2` | `==2.16.0` | `requirements.txt:4` | Used only in `tests/test_agent.py:14,310,317` (`httpx2.Client`, `httpx2.MockTransport`, `httpx2.Response`) to mock the OpenAI HTTP transport. Test-only, yet declared in the runtime file. Package name is unusual (not `httpx`); not checked against PyPI (no network or install performed) |

Stdlib-only modules are used elsewhere (`csv`, `json`, `sqlite3`, `hashlib`, `argparse`, `concurrent.futures`, `threading`, `http`, `urllib`, `subprocess`, `dataclasses`, `base64`, `shlex`, `tempfile`, `socket`, `shutil`, `unittest`). No other third-party imports were found in the code.

Dependency notes:
- All four pins use exact `==`. No lock file (no `poetry.lock`, `uv.lock`, `Pipfile.lock`) and no hash pins. No `constraints.txt`.
- `openai==3.37.0` is a major-version number well beyond the 1.x line this analyst knows from training; it is reported as declared, not validated.
- `pytest` and `httpx2` are dev/test deps mixed into `requirements.txt`; there is no `requirements-dev.txt` split.

## Python version / build system / packaging

- Python version: README line 208 says "Python 3.11 or newer." CI pins `python-version: "3.11"` (`.github/workflows/tests.yml:14`). README badge: `Python-3.11` (README line 8, linking to `requirements.txt`). No `requires-python` field anywhere.
- Build system: none. `pyproject.toml` (3 lines) has only `[tool.pytest.ini_options]`; there is no `[build-system]` and no `[project]` table. The project is not pip-installable as a package; it is run as scripts (`python main.py`, `python ghost/validate.py`, `python evaluation/main.py`).
- Import style: `ghost` is imported as a package from the repo root (`pythonpath = ["."]` in pytest config makes this work under pytest). `ghost/__init__.py` is a single docstring line.
- Ignored artifacts (`.gitignore`): `.env`, `.env.*` (except `.env.example`), `dataset/`, `runs/`, `output.csv`, `code.zip`, `log.txt`, `__pycache__/`, `.pytest_cache/`, `.venv/`, `*.pyc`.
- Gap: `.gitignore` does NOT list `cache/`, which is the default runtime cache directory (`ghost/agent.py:111` `cache_path` default `<repo>/cache/agent_calls.jsonl`; `ghost/llm.py:19` `CACHE = .../cache`). The README says model-response caches are intentionally not redistributed (README lines 297-299), so this is a latent commit risk, not a current leak (no `cache/` dir is in this checkout).

## LLM providers, model names, env vars (names only, never values)

Provider: OpenAI only (Responses API via `openai` SDK). No other provider SDK is imported. Grep for other providers returned nothing.

Model names:
- `gpt-6-luna` is the only model in use. Defaults at:
  - `ghost/agent.py:91` (`AgentConfig`-level reference), `ghost/agent.py:108` (`AgentConfig.model` default), `ghost/agent.py:120` (env fallback), `ghost/llm.py:16` (`PRICES` key), `ghost/intake.py:39`, `ghost/vision.py:32`.
  - README line 156: "Final run on all 518 evaluation requests (`gpt-6-luna`, low reasoning, eight workers)."
- Pricing table: `ghost/llm.py:16` `PRICES = {"gpt-6-luna": (0.10, 0.01, 0.50)}`. Tuple meaning and units are not documented in code. Inference (not stated): likely (input, cached input, output) USD per 1M tokens. Cross-check: README totals (13,734,621 input, 354,814 output, USD 0.4747) only reconcile if roughly 12M of input is billed at the cached rate; the README does not say this.
- `ghost/llm.py:17` `EFFORT = "low"` is hard-coded. `ghost/agent.py:132` rejects any `GHOST_AGENT_EFFORT` value other than `"low"`.

Environment variables (names only):

| name | read at | default in code | purpose |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | `ghost/llm.py:22`, `ghost/agent.py:199`; set in `.env.example:1` (blank) | none (raises RuntimeError if unset on live cache miss, `ghost/llm.py:23-24`) | API credential |
| `OPEN_AI_API` | `ghost/llm.py:22` (fallback) | none | alternate key name fallback |
| `open_ai_key` | `ghost/llm.py:23` (fallback) | none | alternate key name fallback |
| `GHOST_AGENT_MODEL` | `ghost/agent.py:121` | `gpt-6-luna` | model; must be a key in `PRICES` |
| `GHOST_AGENT_EFFORT` | `ghost/agent.py:122` | `low` | must equal `low` |
| `GHOST_AGENT_MAX_TOOLS` | `ghost/agent.py:123` | `24` | tool calls per case |
| `GHOST_AGENT_WORKERS` | `ghost/agent.py:124` | `8` | thread workers |
| `GHOST_AGENT_BUDGET_USD` | `ghost/agent.py:125` | `3` (`3.0` in dataclass) | hard spend cap |
| `GHOST_AGENT_TIMEOUT` | `ghost/agent.py:126` | `120` | per-call timeout, seconds |
| `GHOST_AGENT_MAX_OUTPUT` | `ghost/agent.py:127` | `2600` | max output tokens per call |
| `GHOST_AGENT_CACHE` | `ghost/agent.py:128` | `<repo>/cache/agent_calls.jsonl` | cache file path |

Config validation (`ghost/agent.py:131-134`): raises `ValueError` if model not in `PRICES`, effort != `low`, or any numeric limit <= 0.

Only `OPENAI_API_KEY` appears in `.env.example`. The other variables and the alternate key names are not documented in `.env.example`; README line 248 lists the `GHOST_AGENT_*` names (not the alternate key names).

## Run commands (setup, run, eval, tests) as documented

Setup (README lines 210-214):
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest
```

Offline demo, no model, no network (README lines 219-220):
```bash
python main.py --offline --sample --dataset evaluation/custom_cases/tombstone_pii --run-dir runs/demo
cat runs/demo/sample_predictions.csv
```
Flags confirmed in `main.py:117-126`: `mode` (audit|serve), `--offline`, `--sample`, `--dataset` (default `dataset`), `--run-dir` (default `runs/final`), `--ocr-crosscheck`, `--case`, `--explain`, `--port` (default 8080).

Scoring a custom case (README lines 231-233):
```bash
python evaluation/main.py --dataset evaluation/custom_cases/tombstone_pii \
    --answers evaluation/custom_cases/tombstone_pii/sample_output.csv
```
Flags confirmed in `evaluation/main.py:77-80`: positional `predictions` (optional), `--dataset`, `--answers`.

Challenge data run (README lines 240-245; dataset must be downloaded separately into `dataset/`):
```bash
export OPENAI_API_KEY=...         # PowerShell: $env:OPENAI_API_KEY = "..."
python main.py --run-dir runs/final                  # writes output.csv
python ghost/validate.py output.csv --dataset dataset
python main.py audit --case case_123 --explain       # one request, with its tool trace
python main.py serve --port 8080                     # POST {"case_id": "case_123"}
```
Confirmed: `ghost/validate.py:93-94` takes `output` (default `output.csv`) and `--dataset`. Note: the README's run-dir default writes to `runs/final`, but the README "writes output.csv" comment does not say the file lands at repo root; `main.py` default run dir is `runs/final`, so `output.csv` location depends on the code path (not traced here).

Tests: `python -m pytest` (CI runs `python -m pytest -q`). README line 258: three tests need the challenge dataset and skip without it.

## CI / automation

- Single workflow: `.github/workflows/tests.yml` named `tests`.
- Triggers: `push:` and `pull_request:` (lines 4-5), all branches.
- Job `pytest` on `ubuntu-latest` (line 9).
- Steps: `actions/checkout@v4`; `actions/setup-python@v5` with `python-version: "3.11"`, `cache: pip`, `cache-dependency-path: requirements.txt` (lines 12-16); `pip install -r requirements.txt`; `python -m pytest -q` (line 18).
- No matrix (single Python version), no lint/type step, no coverage, no release/publish job, no secrets referenced, no Dockerfile, no pre-commit config.
- README badge (line 7) points at `G26karthik/ghost-data-still-exists/actions/workflows/tests.yml`.
- Automation gap: CI runs without `OPENAI_API_KEY` and without the dataset, so the three dataset-dependent tests skip in CI; the live model path is never exercised in CI. The offline path and the mocked agent loop (`tests/test_agent.py` using `httpx2.MockTransport`) are what CI covers.

## README claims (scores, accuracy, cost, runtime, design philosophy: quote numbers exactly)

Result and identity:
- Line 10 badge: `HackerRank%20Orchestrate-1st%20of%204%2C650` (renders "1st of 4,650").
- Line 20: "This project took **first place out of 4,650 participants** in HackerRank Orchestrate, October 2026. ... wrote all 518 answers on the evaluation set. I built it with OpenAI Codex as the coding agent."
- Line 22: "The rank is HackerRank's and covers the whole submission. No hidden-set score was published, so none is quoted here."

Measured results (README lines 156-172):
- Line 156: "Final run on all 518 evaluation requests (`gpt-6-luna`, low reasoning, eight workers)."
- Line 160: "**355** `INCOMPLETE`, **153** `COMPLETE`, **10** `NOT_APPLICABLE`" (sum 518, checked).
- Line 161: "First decisions matching the engine's private plan | **503 / 518 (97.1%)**" (503/518 = 97.1%, checked).
- Line 162: "Corrected by the model after a gate diff | 15".
- Line 163: "Fallbacks to the engine | **0**".
- Line 164: "Plans visible to the model before it submitted | 0".
- Line 165: "Fresh model calls / wall time | 5,190 / 1,181 s".
- Line 166: "Estimated cost | **USD 0.47** for the run, about USD 0.001 per request" (0.47/518 = 0.0009, rounds to ~0.001).
- Line 167: "Public samples: statuses / exact rows / steps | 32/32 / 29/32 / 190 of 193, none extra".
- Line 168: "Tests | 63" (14+25+24 = 63, checked against README lines 254-256).
- Line 172: "13,734,621 input and 354,814 output tokens across 5,211 calls, USD 0.4747 including two probe runs. Those are estimates from saved receipts, not an invoice."
- Line 170: "It is not accuracy against the hidden answers, and the engine is not ground truth. The 32 public samples shaped development, so 29/32 is a fit and not a holdout. Twenty-nine evaluation requests have ownership links that rest on the timing tie-break."
- Line 108: "On 224 requests whose account delete is independently linked to the person, the 80-to-40-minute-before-report window held for all 224 and the follow-up timing for 148 of the 151 that could be checked."

Token and cost consistency:
- 13,734,621 input / 518 = ~26.5k input tokens per request; 354,814 output / 518 = ~685 output tokens per request (derived, not stated in README).
- Line 165 says 5,190 fresh calls; line 172 says 5,211 calls including probes (difference 21, consistent with "two probe runs" but not itemized).
- Line 201: "A case gets 24 tool calls (26 when ambiguous) and 2,600 output tokens." Matches code defaults (`ghost/agent.py:122` = 24, `:126` = 2600). The "26 when ambiguous" is not in the config defaults (code not traced further).
- Budget: README line 202 says "A hard USD cap" but gives no figure; code default is USD 3.0 (`ghost/agent.py:125`).

Failure history (lines 178-193):
- Line 180: "0/24 exact on exposed development rows, 15/24 statuses" (model-first).
- Line 181: "Still 0/24 exact, 16/24 statuses".
- Line 182: "Deterministic engine | 18/32 exact".
- Line 183: "Worker-timing correlation | **29/32 exact**, 190/193 steps, none extra".
- Line 184: "Model back in, behind a gate | 503/518 first agreement, 0 fallbacks".
- Line 188: "Follow-up timing, 97/142 became 148/151."
- Line 189: "Fifteen rows changed after a worker's `DELETE_RECORD` on a support target."
- Line 190: "Six rows were corrected."

Design philosophy claims (quotable):
- Line 44: "A language model investigates through read-only tools and writes the plan itself. A deterministic engine audits it privately and a gate decides what gets through. Neither side is trusted alone."
- Line 110: "A logged `DELETE_RECORD` on a support target says the workflow treated it as an attachment, which has a different policy."
- Line 204: "If a person could not be resolved, the runtime raises instead of planning a deletion for someone it could not name."
- Line 262: "The code judge reads Markdown and ignores `.csv`, `.json` and `.log`, so every number in the evaluation reports lives in prose and tables."
- Line 266: "The twenty-nine ownership links that rest on a tie-break were listed by ID in the submission's evaluation report rather than buried."
- Line 267: "Package like a stranger would unpack it ... installed from its declared dependencies only ... its regenerated CSV compared byte for byte with the frozen result."

Limitations (line 289-295): "This is a batch runner with an HTTP wrapper, not a deployed service." "The cheapest real improvement is a first-party batch ID or a per-resource subject key in the worker log."

Claims not verifiable from the scoped files: all accuracy, timing, cost, and "byte for byte" claims rely on artifacts not in this repo (dataset, caches, evaluation reports, which README says are excluded). The `evaluation/` folder contains only the scorer and synthetic cases, so the evaluation report referenced in the README (line 266) is not in this checkout.

## Documentation & presentation quality (structure, diagrams, sections)

Structure:
- Single README (305 lines) with a centred hero banner, 4 shields.io badges, a certificate GIF, then 11 H2 sections: "The result", "What it returns", "How it works", "Measured results", "What failed first", "Bounded by design", "Try it", "Tests", "How it was built", "Layout", "Limitations", "What isn't here", "License". Each H2 has a small SVG icon header (`docs/assets/icons/*.svg`).
- Strong narrative: problem anecdote (lines 24-26), then "What it returns" table, then staged design (five numbered H3 stages with one module per stage, each with a `<sub>` file pointer).
- Honest caveats are placed near claims (line 170 agreement vs accuracy; line 294 "97% agreement ... says nothing about the hidden answers").

Diagrams:
- Three Mermaid diagrams in README: `flowchart LR` pipeline (lines 46-53), `flowchart LR` evidence sources (lines 61-74), `flowchart LR` identity tokens (lines 82-90), and `sequenceDiagram` for the model/gate loop (lines 116-137). Mermaid will render on GitHub.
- Three SVG visuals: `hero.svg` (dark dashboard-style cards: "account_service / account_5 ABSENT verified", "search_service / search_1 PRESENT replica still has it", "analytics_platform / analytics_5 PRESENT still attributable", "integration_service / data_flow_2 ACTIVE sync can recreate it", "backup_service / backup_9 ACTIVE restore not blocked", header "AUDIT AT 2026-09-03T10:00Z"); `cutoff.svg` (timeline with audit_at, result "INCOMPLETE. The replica copy is reported, deleted, and checked absent afterwards."); `timing.svg` (60-second dial with labels +0 s account DELETE, +9.5 s restore block, +10.5 s support redaction, +39.5 s flow disable, +40.5 s analytics/tombstone/legal hold, +51.5 s first follow-up; "Match = within 0.75 s. Ties stay ties.").
- Note on SVG alt text: hero alt is "Ghost Data Still Exists: an audit agent that checks whether deleted actually means deleted" (line 3). Good accessibility practice (alt on all images).
- The hero SVG text in the banner says "AUDIT AT 2026-09-03T10:00Z", which is an illustrative example, not a dataset date. (Not verified against dataset, which is not in the repo.)

Tables:
- "What it returns" (verdict table), "Measured results", "What failed first" (stage/observation/what it taught), "Tests" (suite/count/covers), and an agent-tools table (8 rows). Tables are used for dense facts, not prose.

Presentation weaknesses:
- Layout block (lines 271-287) omits `ghost/llm.py`, `ghost/__init__.py`, and `evaluation/timing_diagnostic.py`.
- The README mixes "gpt-6-luna" as a fixed name; no model-capability or price table explains what "low reasoning" or the `PRICES` tuple means.
- Setup section says "Python 3.11 or newer" but CI and badge say 3.11 only.
- Line 220 writes to `runs/demo` which is gitignored (consistent).
- Certificate GIF is ~4.7 MB, which bloats the README asset load (line 14).
- No CONTRIBUTING, no CHANGELOG, no docs folder beyond assets. Given the view-only license this is expected.

## Notable/differentiating ideas

1. Model proposes, deterministic engine audits, gate compares by content (`ghost/agent_tools.py`): the model never sees the engine's plan; a gate diffs its submission against a private plan and only re-orders/renumbers. Reported first-pass agreement 503/518, 0 fallbacks (README line 161, 163, 164).
2. Worker-timing correlation for anonymous rows (`ghost/activity.py`, README lines 102-110): fixed second-offsets per action type (timing.svg), one-to-one assignment across all requests so one worker action cannot be claimed twice, and explicit `undetermined` on ties (named `activity.earliest_activity_tiebreak`, README line 293).
3. Audit-cutoff semantics (`ghost/state.py`, README line 96): a readback counts only if captured AND recorded at or before `audit_at`; later recreations are excluded along with their citation. Visualised in `cutoff.svg`.
4. Identity as token set (`ghost/identity.py`, README lines 78-92): current and historical emails, phones, and SHA-256 hashes of each old email, so stale records still resolve.
5. Fail-closed identity: runtime raises instead of planning a deletion for an unresolved person (README line 204).
6. Source text treated as data: tests cover an injected instruction in screenshot text and a request that tries to change policy (README line 76; `tests/test_agent.py`).
7. Replayable cache: requests keyed by hash, append-only JSONL that tolerates a truncated last line, finished runs replay with no provider calls (README line 203; `ghost/agent.py` `GHOST_AGENT_CACHE`; `ghost/llm.py:44-45` checks request_hash, model, and reasoning_effort on replay).
8. SQL evidence in sandboxed SQLite: in-memory, ATTACH/DETACH/extension loading denied, only `json_valid` function allowed (README line 200).
9. Spend and runtime bounds: hard budget, per-call timeout, circuit breaker, eight workers, SDK retries off (README lines 201-202).
10. Coverage table: a source that yields nothing shows up as a zero, so silent parser failure is visible (README line 73).
11. Evaluation honesty: explicit "fit not holdout" labelling; the README declines to quote the hidden score (lines 22, 170).
12. Packaging discipline claim: the submission was verified by unpacking into an empty directory and comparing the regenerated CSV byte for byte (README line 267). Not reproducible from this checkout (dataset and reports absent).

Risks and quirks worth noting for a comparison:
- `httpx2` in runtime `requirements.txt` used only by tests; unusual package name.
- `cache/` not gitignored.
- Only `OPENAI_API_KEY` in `.env.example`; alternate key names read silently.
- No `[project]` metadata; not installable as a package.
- Live path not in CI.
- `PRICES` tuple semantics undocumented.
- License forbids reuse, so this repo is read-only for comparison purposes only (LICENSE lines 10-17).
