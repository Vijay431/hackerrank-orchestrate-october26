# Usage Report

Requests in the final run: 518

| Provider | Model | Model calls | Cache hits | Input tokens | Output tokens | Total tokens | Est. cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| openrouter | deepseek/deepseek-v4.1-flash | 422 | 139 | 125107 | 55030 | 180137 | 0.0575 |
| **All** | | **422** | **139** | **125107** | **55030** | **180137** | **0.0575** |

- Average tokens per request: 347.8
- Estimated cost per request: 0.000111 USD
- Calls by purpose: {'intent': 379, 'image_extraction': 43}
- Cost uses `OPENROUTER_PRICE_INPUT` / `OPENROUTER_PRICE_OUTPUT` (USD per million tokens) from the environment.
- Prices used: 0.02 USD per million input tokens and 1.00 USD per million output tokens, read from the public OpenRouter models endpoint on 2026-10-24.
- Run: cold cache (`.cache/` deleted), no `--assume-deletion`; a warm rerun made 0 model calls and produced a byte-identical `output.csv`.
- Update after the final code changes: `output.csv` was regenerated from a warm cache. The intent gate now also classifies the 32 public samples and custom cases so non-deletion requests are excluded from event linking; those extra calls were cache hits or ~26 additional `intent` calls (≈ 6.5k input tokens at the same price), so the totals above change by less than 0.001 USD. The ledger file accumulates evaluation runs, so these totals were not re-derived from it.
