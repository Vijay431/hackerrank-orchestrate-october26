# Proposal

## Why

The repo carries code paths nothing in the submission uses: Makefile targets (`test`, `graph`, a ghost `dev`), a unit-test suite superseded by the golden-sample evaluation, development-only CLI flags (offline mode, stub output, report toggles), and test-only seams. Each one is surface the README, AGENTS.md and the AI interview must explain. Separately, an uncommitted edit to `code/paths.py` writes `output.csv` under `dataset/`, which breaks the output-file contract (`output.csv` at the repository root, AGENTS.md §6.1 and §6.7).

## What Changes

- Remove the Makefile `test` and `graph` targets and the `dev` entry in `.PHONY` (it has no target). Keep `help`, `install`, `run`, `eval`, `validate`, `usage`, `package`.
- Delete `tests/`, `.pytest_cache/`, the `.pytest_cache/` line in `.gitignore`, and `"tests"` from the `code/package.py` INCLUDE list. Evaluation against the golden dataset (`make eval`) is the only verification.
- **BREAKING (developer CLI):** remove offline mode: `--assume-deletion` from `code/main.py` and `--offline` with its `OFFLINE` global from `code/evaluation/main.py`. A keyless run still works when `.cache/` is warm.
- **BREAKING (developer CLI):** remove `--stub` from `code/main.py`, and `--label` and `--no-report` from `code/evaluation/main.py`. The score-history label becomes the constant `run`, and the report is always written.
- Remove the unused optional positional arguments from `code/usage_report.py` (ledger path) and `code/validate_output.py` (output and request paths).
- Keep `--requests` and `--output` on `code/main.py`. The evaluation harness passes them when it runs the pipeline on the samples and custom cases.
- Remove dead intent code: `intent.prior_classifications`, the always-empty `context` parameter of `classify`/`classify_all`, and the `lambda r: []` argument in `code/main.py`. The prompt text sent to the model stays byte-identical, so cached responses stay valid.
- Remove the unused `loader.load_activity()` call in `code/main.py` (intent branch).
- Remove the test-only constructor parameters of `LLMClient` (`transport`, `cache_dir`, `ledger`, `sleep`). The client uses the module defaults directly.
- Revert `code/paths.py` to `OUTPUT = ROOT / "output.csv"` and regenerate the root `output.csv`.
- Update the README (pytest, `make dev`, `make test`, `make graph`, offline-mode lines), AGENTS.md §10 (`make graph`), and the `code/evaluation/main.py` usage docstring.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No requirement in `openspec/specs/deletion-audit/spec.md` covers the removed flags, targets or tests. The submission run, the evaluation, warm-cache keyless runs and `output.csv` at the repository root all behave as specified. The change declares `skip_specs: true`.

## Impact

- Code: `Makefile`, `code/main.py`, `code/evaluation/main.py`, `code/intent.py`, `code/llm.py`, `code/usage_report.py`, `code/validate_output.py`, `code/package.py`, `code/paths.py`.
- Removed: `tests/` (5 files), `.pytest_cache/`.
- Docs: `README.md`, `AGENTS.md` §10, `.gitignore`.
- Outputs: `output.csv` at the repository root is regenerated and must match HEAD byte for byte. `make eval` must report the same headline score with no new model calls, given a warm `.cache/`.
- `code.zip` no longer contains `tests/`.
- Dependencies: none added or removed (`pytest` is not in `code/requirements.txt`).
