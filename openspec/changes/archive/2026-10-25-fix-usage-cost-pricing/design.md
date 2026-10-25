# Design

## Context

`LLMClient` in `code/llm.py` owns `MODEL`/`PROVIDER`. `code/usage_report.py` sums ledger tokens per (provider, model) and prices them only from env vars. See proposal.md.

## Goals / Non-Goals

**Goals:**
- Numeric, reproducible cost with no setup.
- Price lives next to the model it belongs to.

**Non-Goals:**
- Live price fetching, LiteLLM, or billed `usage.cost` capture (LiteLLM has no entry for this OpenRouter route; billed cost would need a full re-run).
- Ledger format change.

## Decisions

- **Constant `PRICE_PER_M = (0.02, 1.0)` in `llm.py` next to `MODEL`.** Single model, fixed value; changing the model forces updating the price in the same place. Alternative (config file / price table) is speculative for one model.
- **Env vars override the constant.** Keeps existing README contract; report line says "user-provided default" vs "environment".
- **Remove the `unknown` path.** Price is always known, so the branch is dead.

## Risks / Trade-offs

- [Price drifts from OpenRouter listing] → Report states the price used; README notes where it was taken from.
- [Model changed without price update] → Constants adjacent in `llm.py`.
