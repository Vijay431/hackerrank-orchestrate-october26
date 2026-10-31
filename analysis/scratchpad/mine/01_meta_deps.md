# 01 Meta and dependencies (read-only analysis)

Scope read: README.md, Makefile, code/requirements.txt, .env.example, .gitignore, .claudeignore, .graphifyignore, agent_trace_instructions.md (skimmed), openspec/config.yaml, openspec/specs/deletion-audit/spec.md (skimmed), openspec/changes/archive listing, .claude/ names. Code files were grepped only for env vars, models, imports, paths. dataset/ and graphify-out/ contents were not analysed (existence only).

## Folder architecture (full tree with one-line purpose per file/folder)

Tracked files: 185 (`git ls-files | wc -l`), excluding `dataset/` and `graphify-out/` as requested.

```
.
├── .claude/                              Claude Code harness wiring for OpenSpec (tracked)
│   ├── commands/opsx/{apply,archive,continue,explore,new,propose,sync,update,verify}.md   9 slash-command stubs
│   └── skills/openspec-{apply-change,archive-change,continue-change,explore,new-change,propose,sync-specs,update-change,verify-change}/SKILL.md   9 skills
├── .claudeignore                         Claude Code ignore: .env*, .venv/, .cache/, __pycache__/, graphify cache, code.zip
├── .env.example                          One line `OPENROUTER_API_KEY=` (template, no value)
├── .gitignore                            Ignores .env*, .cache/, code.zip, __pycache__, .venv, graphify internals, dated graphify snapshots
├── .graphifyignore                       graphify exclusions: .claude/, openspec/, .env*, log.txt, output.csv, graphify-out/, caches
├── AGENTS.md                             429 lines; single source of truth for agent behaviour, logging (§2, §5) and project contract (§6)
├── CLAUDE.md                             One line: `@AGENTS.md` (pulls AGENTS.md into Claude Code)
├── Makefile                              30 lines; thin aliases over README commands (install, run, eval, validate, usage, package, help)
├── README.md                             216 lines; quick start, dataset map, output contract, eval/usage requirements, packaging, solution notes, architecture table
├── agent_trace_instructions.md           130 lines; how to submit agent traces (Claude Code, Codex, Antigravity paths) as agent-trace.zip
├── problem_statement.md                  162 lines; participant-facing challenge specification
├── log.txt                               ~38 KB session log required by AGENTS.md §2 (append-only)
├── output.csv                            ~632 KB root-level predictions (submission artifact)
├── code/                                 Python solution (the code.zip payload)
│   ├── main.py                           90 lines; CLI entry (`--requests`, `--output`); runs audit over all cases and writes output.csv
│   ├── loader.py                         99 lines; typed loaders for dataset CSVs
│   ├── identity.py                       87 lines; resolves request email to user_id; current + historical email/phone/hash set
│   ├── ingest.py                         456 lines; normalises SQL, JSON, log, text, PDF (pypdf), image evidence into Fact records
│   ├── state.py                          373 lines; fact index, resource-to-subject linking, ActivityLinker, state at audit_at per store
│   ├── policy.py                         67 lines; data category resolution and treatment from deletion_rules.csv
│   ├── planner.py                        152 lines; status decision, finding/remediation/verification steps, ordering, serialisation
│   ├── intent.py                         40 lines; one LLM intent call per case, ThreadPoolExecutor with WORKERS = 6 (intent.py:12)
│   ├── llm.py                            119 lines; OpenRouter client, on-disk response cache (.cache/llm), usage ledger, PRICE_PER_M, .env reader
│   ├── vision.py                         82 lines; Pillow tiling/upscaling of screenshots and per-tile transcription
│   ├── prompt_registry.py                16 lines; versioned prompt loading from prompts/
│   ├── progress.py                       33 lines; staged progress output
│   ├── paths.py                          10 lines; repo-root-relative path constants (ROOT, DATASET, CACHE, OUTPUT, EVAL_DIR)
│   ├── validate_output.py                82 lines; checks the output.csv contract
│   ├── usage_report.py                   72 lines; writes evaluation/usage_report.md from the usage ledger
│   ├── package.py                        45 lines; builds code.zip from code/, README.md, Makefile, .env.example, evaluation/
│   ├── requirements.txt                  3 unpinned packages (see Dependencies)
│   ├── prompts/
│   │   ├── intent/v1.txt, v2.txt         intent-classification prompt versions (v2 fences untrusted request text)
│   │   └── image_tile/v1.txt             screenshot tile transcription prompt
│   └── evaluation/
│       ├── main.py                       210 lines; scores samples and custom cases, citation validity, determinism, writes evaluation/evaluation_report.md
│       └── cases/{requests,expected,notes}.csv   3 participant-authored custom cases (header + 3 rows each)
├── evaluation/                           Generated reports at ROOT level (not under code/)
│   ├── evaluation_report.md              76 lines; generated by code/evaluation/main.py
│   └── usage_report.md                   13 lines; generated by code/usage_report.py
├── openspec/                             Spec-driven change workflow
│   ├── config.yaml                       schema `spec-driven`; context pins model to deepseek/deepseek-v4.1-flash via OpenRouter SDK
│   ├── specs/deletion-audit/spec.md      main spec (output contract, step schema, ordering, serialisation, intent gate)
│   ├── specs/.gitkeep
│   └── changes/archive/                  4 archived changes (listed below), plus .gitkeep
│       ├── 2026-10-25-compact-eval-history/        proposal, design, tasks, spec delta, .openspec.yaml
│       ├── 2026-10-25-deletion-audit-pipeline/     proposal, design, tasks, spec delta, .openspec.yaml
│       ├── 2026-10-25-fix-usage-cost-pricing/      proposal, design, tasks, spec delta, .openspec.yaml
│       └── 2026-10-25-remove-dead-code/            proposal, design, tasks, .openspec.yaml (no spec delta)
├── graphify-out/                         Tracked graphify artefacts: GRAPH_REPORT.md, graph.html, graph.json (contents not analysed)
├── dataset/                              Participant data (not analysed per scope): 518-request CSV, samples, identities, audit log, activity, rules, evidence manifest, evidence/ tree
└── analysis/                             Untracked orchestration scratch space created for this review (not in git)
```

Notes:
- `code/evaluation/` contains only `main.py` and `cases/`. The generated reports are NOT there (see README contradiction in Documentation section).
- No `tests/`, no `.github/`, no `pyproject.toml`, no `setup.cfg`, no lockfile, no `Dockerfile`.

## Dependencies & exact versions (table: package | version spec | where declared | purpose)

| package | version spec | where declared | purpose |
| --- | --- | --- | --- |
| `pypdf` | none (unpinned) | `code/requirements.txt:1` | PDF text extraction; lazily imported in `code/ingest.py:358` |
| `openrouter` | none (unpinned) | `code/requirements.txt:2` | OpenRouter Python SDK; lazily imported in `code/llm.py:55` |
| `Pillow` | none (unpinned) | `code/requirements.txt:3` | Screenshot tiling and upscaling in `code/vision.py:10` (`from PIL import Image`) |

- Total declared: 3 packages, zero version specifiers, zero hashes, no extras.
- Stdlib modules in use include `sqlite3` (ingest.py:8), `concurrent.futures` (intent.py:4), `zipfile` (package.py:6), `hashlib` and `base64` (llm.py:6-7), `threading` and `time` (llm.py:10-11), `subprocess` (evaluation/main.py:8), `tempfile` (evaluation/main.py:10), `argparse` (main.py:2).
- No dev dependencies declared (no pytest, ruff, mypy, black).
- Nothing pins the Python toolchain or transitive versions; a fresh install can resolve differently over time.

## Python version / build system / packaging

- Python version: README.md:172 states "Requires Python 3.10+." No `python_requires`, no `.python-version`, no `pyproject.toml`, no CI matrix. Nothing in code/ enforces the version.
- Build system: none. There is no `pyproject.toml`, `setup.py`, or `setup.cfg`. Installation is `pip install -r code/requirements.txt` into a venv.
- Packaging: `code/package.py` builds `code.zip` itself. `INCLUDE = ["code", "README.md", "Makefile", ".env.example", "evaluation"]` (package.py:13). `SKIP_PARTS` excludes `__pycache__`, `.venv`, `venv`, `.cache`, `dataset`, `node_modules` (package.py:14). Docstring says `.env` files, `output.csv`, and `log.txt` are excluded (package.py:3). Note: `evaluation` is packaged from the ROOT, which matches the actual output location and not the README's `code/evaluation/` instruction.
- The README packaging section (README.md:129-141) also gives raw `zip -r` and PowerShell `Compress-Archive` commands that do not match `package.py`'s include list exactly (README's zip includes `README.md code` only, relying on `code/evaluation/`).

## LLM providers, model names, env vars (names only, never values)

Providers and models:
- Provider: `openrouter` (`code/llm.py:18`, `PROVIDER = "openrouter"`).
- Model: `deepseek/deepseek-v4.1-flash` (`code/llm.py:17`, `MODEL = ...`). The only model in code and in `openspec/config.yaml:10`, which says to use "only" this model.
- Temperature: `temperature=0` (`code/llm.py:64`).
- Price constant: `PRICE_PER_M = (0.02, 1.0)` USD per 1M (input, output) tokens (`code/llm.py:19`), described in code as the OpenRouter list price for MODEL.
- Calls: intent gate (one call per case, `code/intent.py`), and screenshot tile transcription (`code/vision.py`, prompt `code/prompts/image_tile/v1.txt`). Usage ledger file: `CACHE / "usage_ledger.jsonl"` (`code/llm.py:21`). Cache directory: `CACHE / "llm"` (`code/llm.py:20`), where CACHE = `ROOT/.cache` (`code/paths.py:7`).

Environment variables (names only):
- `OPENROUTER_API_KEY`: read via `os.environ.get` (`code/llm.py:52`), falling back to a literal parser of repo-root `.env` (`code/llm.py:38-40`, `_dotenv_value`). Listed in `.env.example`.
- `OPENROUTER_PRICE_INPUT`, `OPENROUTER_PRICE_OUTPUT`: optional price overrides, read in `code/usage_report.py:37`. Documented at README.md:202.

Secret handling:
- `.env*` is git-ignored and claude-ignored (`.gitignore:1`, `.claudeignore:1`); `!.env.example` is re-included.
- `code/llm.py` deliberately reads `.env` as literal text ("no expansion or command substitution", llm.py:39). The Makefile does not include `.env` (Makefile:4 comment; commit `security: stop Makefile evaluating .env`).

## Run commands (setup, run, eval, tests) as documented

Documented in README.md:172-183 (raw commands):
```
python3 -m venv .venv && source .venv/bin/activate
pip install -r code/requirements.txt
cp .env.example .env
export OPENROUTER_API_KEY=...
python code/main.py                         # writes ./output.csv (518 rows)
python code/validate_output.py              # checks the output contract
python code/evaluation/main.py              # scores 32 samples and custom cases, writes evaluation/evaluation_report.md
python code/usage_report.py                 # writes evaluation/usage_report.md from the last run's ledger
```

Makefile aliases (Makefile:2-30), README.md:185-193:
- `make install`: `python3 -m venv .venv` then `$(PY) -m pip install -r code/requirements.txt`.
- `make run`: `$(PY) code/main.py` then `$(PY) code/validate_output.py`.
- `make eval`: `$(PY) code/evaluation/main.py`.
- `make validate`, `make usage`, `make package`, `make help` (help greps `^[a-z]+:.*## `, Makefile:9-10).
- `PY ?= .venv/bin/python` (Makefile:2). Every target except `install` therefore needs `.venv` to exist first. Calling `make run` on a clean clone before `make install` fails.

Tests: none. No test directory, no pytest config, no `make test` target. The README mentions no tests. Git history commit `refactor: remove dead Makefile targets, CLI flags, offline mode and tests` (2026-10-25) shows tests were removed deliberately.

Reproducibility claims relevant to running:
- README.md:198: responses cached under `.cache/`, so a rerun with a warm cache makes no model calls and writes a byte-identical `output.csv`.
- README.md:200: "A keyless run needs a warm `.cache/`." But `.cache/` is git-ignored (`.gitignore:3`) and excluded from `code.zip` (`package.py:14`). A reviewer who clones the repo or unpacks `code.zip` has no cache, so a keyless run cannot reproduce output. This gap is not mentioned in the README.

## CI / automation / dev tooling (Makefile targets, openspec, graphify, claude skills)

- CI: none. No `.github/` directory, no workflow files, no pre-commit config, no lint or type-check configuration.
- Makefile: 7 targets (install, run, eval, validate, usage, package, help), described above. `.DEFAULT_GOAL := help` (Makefile:6).
- OpenSpec: `openspec/config.yaml` with `schema: spec-driven` and a project `context` that points at `@problem_statement.md` and `@AGENTS.md` and restricts the model to `deepseek/deepseek-v4.1-flash` (config.yaml:7-10). Main spec at `openspec/specs/deletion-audit/spec.md`, with requirements for output contract, step schema, ordering, deterministic serialisation, and the intent gate (visible at spec.md:9-38). Four archived changes dated 2026-10-25 (listed in the tree). Each change folder has `proposal.md`, `design.md`, `tasks.md`, optional spec delta, and `.openspec.yaml`.
- `.claude/`: 9 OpenSpec slash-command stubs in `.claude/commands/opsx/` (apply, archive, continue, explore, new, propose, sync, update, verify) and 9 matching skills in `.claude/skills/openspec-*/SKILL.md`. These are the Claude Code harness integration.
- Graphify: `graphify-out/` is tracked (GRAPH_REPORT.md, graph.html, graph.json). `.graphifyignore` excludes `.claude/`, `openspec/`, `log.txt`, `output.csv`, and secrets. `AGENTS.md` §10 says to query `graphify-out/` first and run `graphify update .` after code changes. The graph report header says 385 nodes, 740 edges, and 19 communities, dated 2026-10-25.
- Agent logging: `AGENTS.md` §2 and §5 require every turn to be appended to root `log.txt` with `tool=` and `model=` fields. `log.txt` is tracked and is part of the submission artefact set.
- Trace submission: `agent_trace_instructions.md` tells participants to zip per-harness session files as `agent-trace.zip`.

## README claims (scores, accuracy, cost, runtime — quote numbers exactly)

The README contains no accuracy, score, cost, or runtime results. Every numeric claim it makes is a configuration or dataset fact:
- README.md:9 and 49: "518 requests" (`deletion_requests.csv`).
- README.md:50: "32 sample requests".
- README.md:75: "The final file must contain 518 data rows sorted by `case_id` (plus the header row)."
- README.md:123: "One answer row for each of the 518 requests".
- README.md:172: "Requires Python 3.10+."
- README.md:179: `python code/main.py   # writes ./output.csv (518 rows)`.
- README.md:181: "scores the 32 samples and custom cases, writes evaluation/evaluation_report.md".
- README.md:202: "$0.02 input / $1.00 output per 1M, `PRICE_PER_M` in `code/llm.py`".
- README.md:213: "Cached one-call-per-case intent gate (6 workers)".
- README.md:216: "Everything except intent classification and image reading is plain, deterministic code."

Actual results live only in generated files (not README):
- `evaluation/evaluation_report.md` (root): header line "Generated by `python code/evaluation/main.py`. Scores are 0-100." Case-level deletion-status accuracy 100.00; step-level accuracy 96.89 (as read from the first 10 lines). Remaining metrics not read.
- `evaluation/usage_report.md` (root): "Requests in the final run: 518". One row: `openrouter | deepseek/deepseek-v4.1-flash | 852 calls | 14781 cache hits | 269184 input | 89580 output | 358764 total | 0.0950 USD`. Average 692.6 tokens per request. Estimated cost 0.000183 USD per request. Calls by purpose: `{'intent': 809, 'image_extraction': 43}`.
- Check: 852 calls = 809 + 43. Total cost 0.0950 USD matches the stated price (269184 × 0.02 / 1e6 + 89580 × 1.0 / 1e6 ≈ 0.0054 + 0.0896 ≈ 0.0950).

## Documentation & presentation quality

Strengths:
- README is structured with a clear Quick Start, dataset table, output contract, eval requirements, packaging checklist, solution notes, and an architecture table (README.md:204-216). The architecture table maps each module to its role.
- README.md:161-168 explains identity rules concisely (case-insensitive emails and hashes, digits-only phone comparison, names never sufficient).
- AGENTS.md is thorough (429 lines), with explicit log format and a per-turn checklist.

Issues found (file:line):
1. Contradiction about evaluation report location. README.md:91-94 says `code.zip` must include `code/evaluation/evaluation_report.md` and `code/evaluation/usage_report.md`. README.md:99 says "Place `evaluation_report.md` and `usage_report.md` inside `code/evaluation/`". But the code writes to the ROOT `evaluation/` directory: `code/paths.py:10` (`EVAL_DIR = ROOT / "evaluation"`), `code/evaluation/main.py:19`, `code/usage_report.py:67`. README.md:181-182 also says `evaluation/evaluation_report.md` and `evaluation/usage_report.md`. README.md:145 hedges ("or add `evaluation` to the archive command above if you placed them in a top-level `evaluation/` directory"). AGENTS.md §6.8 uses the root `evaluation/` path. Result: the README is internally inconsistent about the required location.
2. The README packaging command (README.md:134) zips `README.md code` only. Following it omits the root `evaluation/` reports, which the code actually writes. `package.py` does include `evaluation`.
3. Keyless reproduction gap (README.md:198-200): the claim that a warm `.cache/` replays results conflicts with `.cache/` being git-ignored and not packaged.
4. The `make run` path depends on `.venv` existing (Makefile:2), which the README does not note at README.md:185-193.
5. `README.md:121` and `README.md:159` headings are fine, but the README has no troubleshooting section and no mention of how to rerun a single case.
6. The README has no badges, screenshots, or example output snippet. It is plain Markdown tables.
7. `log.txt` is about 38 KB and is tracked as a submission artefact. It is append-only by rule, so it grows with every session.
8. Typo-level: README.md:96 says "at least three additional evaluation cases". `code/evaluation/cases/` has exactly three rows, so the minimum is met with no margin.

## Git history shape

- Total commits: 52 when first counted, 53 when re-checked later in the same run (a new commit `e04c330` "Log session start for solution comparison analysis", dated 2026-10-31, landed from another agent during this analysis). Tracked files: 185.
- Date range: 2026-10-21 (oldest, "chore: update user identity" and "chore: add user audit log") to 2026-10-25 for the 52 original commits; the newest commit is dated 2026-10-31.
- Commits per day (`git log --format='%ad' --date=short | sort | uniq -c`, taken with 53 commits): 4 on 10-21, 5 on 10-22, 15 on 10-23, 16 on 10-24, 12 on 10-25, 1 on 10-31.
- 36 of the 53 commit subjects start with `chore:` (dataset, problem-statement, log and graph refreshes).
- Commit subjects are dominated by `chore:` (dataset and problem-statement updates, log/graph refreshes). The engineering work appears in a burst on 2026-10-24 and 2026-10-25: "Deletion-audit pipeline: full implementation and final run (all tasks) (#1)", "security: stop Makefile evaluating .env", "refactor: versioned prompt registry", "fix: price usage report at the model's OpenRouter list price", "refactor: remove dead Makefile targets, CLI flags, offline mode and tests".
- A merge commit names `origin/claude/clever-bell-b7cqef`, which suggests a Claude Code worktree branch merged back to main.
- Commit ordering is not strictly monotone (for example, a 2026-10-24 security commit sits below 2026-10-25 commits), which suggests rebased or cherry-picked history.
- Shape: a long dataset-building phase (roughly half the commits, 10-23 to 10-23), a short pipeline burst (10-24 to 10-25), then cleanup and documentation churn in the last day.

## Notable ideas

1. Cache-keyed LLM calls (`code/llm.py`, cache at `.cache/llm`, ledger at `.cache/usage_ledger.jsonl`). This makes reruns deterministic and cheap, and gives exact token accounting for the usage report.
2. Screenshot tiling (`code/vision.py`): cut into column and detail-panel tiles, upscale, transcribe per tile. A practical fix for models that misread full-size screenshots (README.md:200).
3. Versioned prompts (`code/prompt_registry.py`, `code/prompts/intent/v1.txt` and `v2.txt`). v2 "fences untrusted request text" per git history, a prompt-injection hardening.
4. Deterministic planner: LLM is used only for intent classification and image transcription (README.md:216). Everything else (identity, policy, state, step ordering) is code, which is auditable.
5. Evaluation harness ignores the 518 requests and scores only the 32 public samples plus custom cases (`code/evaluation/main.py`, report header). Keeps the hidden set out of tuning.
6. Pricing taken from a constant with env override (`code/llm.py:19`, `code/usage_report.py:37`), so usage cost is reproducible from the ledger.
7. OpenSpec plus `.claude/` skills integrated into the repo so the spec drives changes and archives are dated and kept (`openspec/changes/archive/`).
8. Gap to consider: no tests, no pinned dependencies, no CI. A small pytest suite over `planner.py` ordering and `validate_output.py` would protect the contract cheaply. Pinning `openrouter`, `pypdf`, and `Pillow` would stop silent SDK drift.
9. Gap to consider: README packaging instructions and the evaluation report path disagree (see Documentation section). Fixing the README is a one-line change.
10. Gap to consider: `make run` needs `.venv` first. A `make` target that checks for the venv, or a `PY ?= python3` default, would remove a common first-run failure.
