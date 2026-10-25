# Spec Delta

## MODIFIED Requirements

### Requirement: Usage report
The system SHALL record provider, model, call count, input tokens, and output tokens for the final full run and write `evaluation/usage_report.md` with totals, average tokens per request, estimated total cost, and estimated per-request cost, counting cache hits separately from real calls. Cost SHALL always be numeric, computed from the model's per-token price, and the report SHALL state the input and output price (USD per 1M tokens) used.

#### Scenario: Usage summary
- **WHEN** the full 518-case run completes
- **THEN** `evaluation/usage_report.md` lists `deepseek/deepseek-v4.1-flash` with call counts, tokens, and cost estimates

#### Scenario: Default price
- **WHEN** the usage report is generated with no price environment variables set
- **THEN** cost is computed at $0.02 per 1M input tokens and $1.00 per 1M output tokens and the report states those prices

#### Scenario: Price override
- **WHEN** `OPENROUTER_PRICE_INPUT` and `OPENROUTER_PRICE_OUTPUT` are set
- **THEN** cost uses those prices and the report states they came from the environment

#### Scenario: Cache hits are free
- **WHEN** the ledger contains cache-hit entries
- **THEN** they add no tokens and no cost
