# Tasks

## 1. Generator

- [x] 1.1 In `code/evaluation/main.py`, skip appending the `run` row when its score cells equal the last history row's; verify two consecutive `make eval` runs leave the history row count unchanged.
- [x] 1.2 Verify a changed score still appends: temporarily alter a score in the old report's last row, run `make eval`, confirm a new row appears, then restore.

## 2. Report cleanup

- [x] 2.1 Collapse legacy identical-score history rows in `evaluation/evaluation_report.md` as described in design.md; verify no two adjacent rows share all seven score cells.
- [x] 2.2 Reword the `--offline` sentence in the failures section; verify `grep -n -- "--offline" evaluation/evaluation_report.md` returns nothing.
- [x] 2.3 Run `make eval`; verify metrics still read headline 97.80, the history gains no row, and the failures section is unchanged.
