## ADDED Requirements

### Requirement: Compact score history
The evaluation SHALL NOT append a score-history row whose label is `run` when its six scores and headline equal those of the last history row.

#### Scenario: Repeat run with unchanged scores
- **WHEN** the evaluation completes with scores identical to the last history row
- **THEN** the score history gains no new row

#### Scenario: Changed scores
- **WHEN** any score differs from the last history row
- **THEN** a new `run` row is appended

### Requirement: Failures section preserved
Regenerating `evaluation/evaluation_report.md` SHALL keep the existing "Failures found and improvements made" section verbatim, and SHALL NOT describe CLI flags or modes that no longer exist.

#### Scenario: Regeneration
- **WHEN** the evaluation command rewrites the report
- **THEN** the failures section text equals its previous text
