# Proposal

## Why

`make usage` writes `unknown` for estimated cost because `code/usage_report.py` reads prices only from `OPENROUTER_PRICE_INPUT` / `OPENROUTER_PRICE_OUTPUT`, which are never set. `evaluation/usage_report.md` is a required submission artifact (AGENTS.md §6.8) and must state estimated total and per-request cost.

## What Changes

- Store the model's price (USD per 1M tokens: $0.02 input, $1.00 output, as listed by OpenRouter for `deepseek/deepseek-v4.1-flash`) beside the model name in `code/llm.py`.
- `code/usage_report.py` uses that price by default; the two env vars remain an override.
- Remove the `unknown` cost branch.
- The report states the price used and its source.
- Update the README usage paragraph.

## Capabilities

### New Capabilities

### Modified Capabilities
- `deletion-audit`: "Usage report" requirement now guarantees a numeric cost estimate and a stated price basis.

## Impact

- `code/llm.py`, `code/usage_report.py`, `README.md`, regenerated `evaluation/usage_report.md`.
- No change to model calls, cache, ledger format, or `output.csv`.
