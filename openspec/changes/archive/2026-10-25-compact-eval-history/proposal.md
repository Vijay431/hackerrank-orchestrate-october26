# Proposal

## Why

`evaluation/evaluation_report.md` appends a `run` row to its score history on every `make eval`, so repeat runs pile up identical rows (8 trailing 97.80 rows today). Legacy rows also carry task-number labels and an `--offline` explanation for a mode that no longer exists, which misleads readers. A fresh eval confirmed the metrics are unchanged (headline 97.80), so only the history and its wording are stale.

## What Changes

- The evaluation generator skips appending a `run` row whose six scores and headline equal the previous row.
- One-time cleanup of the committed report: collapse identical-score legacy rows into single milestones, and replace the removed-`--offline` sentence in the failures section.
- The failures section stays preserved across regeneration (already true; now covered by a requirement).

## Capabilities

### New Capabilities

### Modified Capabilities
- `deletion-audit`: add requirements that the report's score history stays compact and that regeneration preserves the failures section.

## Impact

- `code/evaluation/main.py` (`history_rows` / `main` append step)
- `evaluation/evaluation_report.md` (history table, one failures-section sentence)
- No change to scoring, pipeline, `output.csv`, or the usage report.
