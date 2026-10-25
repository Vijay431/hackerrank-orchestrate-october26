# Design

## Context

`code/evaluation/main.py` reads the old report, reuses its history rows (`history_rows`), appends one `run` row, and carries the failures section forward by slicing from `FAIL_HEADING`. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:** stop identical consecutive `run` rows; clean the current report once.

**Non-Goals:** changing scoring, adding timestamps or run counts to rows, auto-generating the failures prose.

## Decisions

- **Dedupe at append time, comparing score cells only.** The new row is the string `| run | s1 | ... | head |`; compare its cells after the label against the last history row's cells. Equal means skip. Alternative: dedupe the whole table on every write; rejected because it would silently delete hand-labelled milestones.
- **Legacy rows cleaned by one-time hand edit of the report**, not by code. Keep one row per distinct score set where a label marks a milestone (`stub`, `offline ... after 8.x`, each `phase*`/`trial*` row); drop unlabelled-in-spirit repeats (`after 3.x`, `after 5.x`, `final-cold-cache`, `sample-only eval`, trailing `run` rows).
- **Failures sentence** about `--offline` is reworded by hand to say phase-labelled rows predate the removal of offline mode and were scored with the intent gate skipped.

## Risks / Trade-offs

- [A real regression that returns to a prior score set is hidden] -> only consecutive identical rows are skipped, so any change in between still shows.
- [Hand edit drifts from generator format] -> run `make eval` after and diff: the table must be unchanged apart from no new row.
