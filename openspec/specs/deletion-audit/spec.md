# deletion-audit Specification

## Purpose

Audits each personal-data deletion request against participant-visible evidence and policy, deciding whether deletion is truly complete and producing ordered, evidence-backed findings, remediation, and verification steps.

## Requirements

### Requirement: Output file contract
The system SHALL write `output.csv` at the repository root with header `case_id,deletion_status,steps_json`, exactly one row per `case_id` in `dataset/deletion_requests.csv`, sorted by `case_id`. `deletion_status` SHALL be `COMPLETE`, `INCOMPLETE`, or `NOT_APPLICABLE`, and `steps_json` SHALL be a valid JSON array.

#### Scenario: Full run row count
- **WHEN** the pipeline runs on the 518-request dataset
- **THEN** `output.csv` contains the header plus 518 data rows sorted by `case_id`, each with a parseable JSON array in `steps_json`

### Requirement: Step object schema
Each step SHALL contain exactly `step_no`, `phase`, `system_id`, `resource_id`, `operation`, `state`, `evidence_id`. `operation` and `state` SHALL be one of the pairs allowed by the problem statement for that phase. `evidence_id` SHALL be a single string.

#### Scenario: No extra or missing fields
- **WHEN** any step is emitted
- **THEN** it has exactly the seven fields and its `(phase, operation, state)` matches an allowed pair

### Requirement: Step ordering
Steps SHALL be ordered by phase (FINDING, REMEDIATION, VERIFICATION), then by the operation's position in the problem statement's operation table, then by `system_id` ascending, then `resource_id` ascending. `step_no` SHALL start at 1 and increase by 1.

#### Scenario: Mixed remediation order
- **WHEN** a case needs DISABLE_DATA_FLOW on `integration_service/data_flow_9522`, DELETE_RECORD on `search_service/search_052`, REDACT_RECORD on `support_platform/support_864`, and ANONYMIZE_RECORD on `analytics_platform/analytics_2034`
- **THEN** remediation steps appear in exactly that order and step numbers are consecutive

### Requirement: Deterministic serialization
Identical inputs and cache contents SHALL produce a byte-identical `output.csv`. JSON in `steps_json` SHALL use sorted keys and compact separators.

#### Scenario: Repeat run
- **WHEN** the pipeline runs twice with the same `dataset/` and `.cache/`
- **THEN** both `output.csv` files are byte-identical

### Requirement: Deletion intent gate
The system SHALL decide from `request_text`, in any language, whether the person authorizes deletion. Access, correction, export, marketing opt-out, or other non-deletion requests SHALL yield `NOT_APPLICABLE` with `steps_json` `[]`, regardless of other fields.

#### Scenario: Non-deletion request
- **WHEN** `request_text` asks only for a copy of the person's data
- **THEN** the row is `NOT_APPLICABLE` with `[]`

#### Scenario: Non-English deletion request
- **WHEN** `request_text` is a Spanish request to delete the account
- **THEN** the case proceeds to the deletion audit

### Requirement: Deterministic LLM calls
Every LLM call SHALL use model `deepseek/deepseek-v4.1-flash` via OpenRouter at temperature 0, and its response SHALL be cached under `.cache/` keyed by model, prompt, and input. A cached response SHALL be reused instead of calling the model.

#### Scenario: Cache hit
- **WHEN** a case's intent was already classified with the same model, prompt, and input
- **THEN** no model call is made and the cached decision is used

### Requirement: One LLM call per case with bounded parallelism
The system SHALL make at most one LLM call per case for intent, plus one call per image file for extraction made before cases run. Case calls SHALL run in parallel with at most 6 concurrent calls, without changing output order.

#### Scenario: Parallel run ordering
- **WHEN** 518 cases are classified with 6 concurrent workers
- **THEN** the output rows remain sorted by `case_id` and match a sequential run

### Requirement: Evidence ingestion
The system SHALL locate files via `dataset/evidence_files.csv` and read their contents: PDFs as text, PNG images through one cached multimodal extraction each, SQL snapshots by executing them in SQLite, and JSON, log, and text files directly. Extracted content SHALL be cached under `.cache/`.

#### Scenario: PDF text available
- **WHEN** `evidence/documents/security_retention_extract.pdf` is ingested
- **THEN** its subject reference, event reference, and retain-until date are available to the audit

### Requirement: Evidence linked by contents only
The system SHALL connect evidence to a case only through identifiers found in its contents, never through the manifest's path, origin, or file order.

#### Scenario: Unrelated file
- **WHEN** an evidence file contains no identifier from the subject's identity set or linked resources
- **THEN** it contributes no finding or verification to that case

### Requirement: Identity resolution
The system SHALL resolve the request email to a `user_id` whether it is current in `user_identities.csv` or historical in `user_audit_log.csv`, and SHALL build an identity set of the `user_id` plus every current and historical email, phone, and email hash.

#### Scenario: Historical email
- **WHEN** the request email appears only as an `old_value` email in `user_audit_log.csv`
- **THEN** the subject's `user_id` is resolved and their current identifiers join the identity set

### Requirement: Resource linking
The system SHALL treat a resource as belonging to the subject when a catalog link event, or evidence content, ties its `resource_id` to an identifier in the identity set. Resource ID prefixes SHALL NOT be assumed to be user IDs.

#### Scenario: Catalog link
- **WHEN** a `LINK_RESOURCE_IDENTITY` event at or before `audit_at` links `search_428` to the subject's email
- **THEN** `search_428` is audited for that case

### Requirement: Audit time cutoff
The system SHALL use only activity with `event_time` at or before `audit_at` and evidence with `captured_at` at or before `audit_at`, and SHALL include relevant events from before `requested_at`.

#### Scenario: Later evidence ignored
- **WHEN** an evidence file proving deletion was captured after `audit_at`
- **THEN** it does not change the case's status or steps

#### Scenario: Capture at audit time
- **WHEN** evidence `captured_at` equals `audit_at`
- **THEN** that evidence is used

### Requirement: Claims are not proof
The system SHALL NOT treat `reported_status` or an activity's `reported_result` as proof of a resource's state. Resource state SHALL come from the latest evidence observation at or before `audit_at`.

#### Scenario: Reported success contradicted
- **WHEN** a deletion activity reports SUCCESS but a later snapshot before `audit_at` still contains the record
- **THEN** the record is PRESENT

### Requirement: Replica drift detection
A record SHALL count as present when any replica snapshot (primary, read, regional, reporting, failover) at or before `audit_at` still contains it after its latest removal from other copies.

#### Scenario: Replica keeps record
- **WHEN** the primary snapshot lacks a record but a later reporting replica snapshot still has it
- **THEN** the record is reported as remaining

### Requirement: Data category classification
Each linked resource SHALL be assigned one `data_category` from `deletion_rules.csv` based on its evidence content. The customer statement in `account_history_report_20260718.pdf` SHALL be classified as `USER_PROFILE`, with `system_id` `account_history_service` and `resource_id` `NST-2026-0718-1842`.

#### Scenario: Customer statement
- **WHEN** a case's subject is the customer named in the account history statement and the file is captured at or before `audit_at`
- **THEN** the statement is treated as a `USER_PROFILE` record requiring deletion

### Requirement: Policy treatment
The system SHALL apply the matching rule in `deletion_rules.csv`: DELETE yields final state ABSENT, REDACT yields REDACTED, ANONYMIZE yields ANONYMIZED, RETAIN yields PRESENT, and a `BACKUP_ARCHIVE` is retained with restore BLOCKED.

#### Scenario: Analytics profile still attributable
- **WHEN** an analytics profile still contains the subject's email
- **THEN** it is reported as exposed PII and remediated with ANONYMIZE_RECORD

### Requirement: Account tombstone treatment
An `ACCOUNT_TOMBSTONE` SHALL keep the stable `user_id` and SHALL have name, email, phone, email hash, and any other direct identifier removed. A tombstone still holding such identifiers SHALL be reported as exposed PII and remediated with REDACT_RECORD.

#### Scenario: Tombstone with email
- **WHEN** `identity_service/tombstone_9178` still holds the subject's email
- **THEN** steps are REPORT_EXPOSED_PII, REDACT_RECORD, VERIFY_RECORD_REDACTED for that tombstone

### Requirement: Legal hold retention
Legal holds SHALL be reported only for real `legal_hold_*` records linked to the subject. The finance register PDF SHALL only confirm whether such a hold is still active and SHALL NOT create steps by itself.

#### Scenario: Register entry without record
- **WHEN** the register lists an order for the subject but no `legal_hold_*` record links to the subject
- **THEN** no legal-hold step is emitted

#### Scenario: Active hold record
- **WHEN** a `legal_hold_*` record links to the subject and its hold is active at `audit_at`
- **THEN** it is retained and verified PRESENT

### Requirement: Security audit retention
A `SECURITY_AUDIT_LOG` record SHALL be retained per `rule_12` while `audit_at` is within its supplied retention period, and verified PRESENT.

#### Scenario: Within retention
- **WHEN** `audit_record_1738` has `retention_until` 2031-12-31 and `audit_at` is in 2026
- **THEN** the record is retained and a VERIFY_RECORD_PRESENT step is emitted

### Requirement: Recreation risk detection
An active sync, import, or connector that can copy the subject's data SHALL be reported as REPORT_ACTIVE_DATA_FLOW, and a backup holding the subject's data whose restore is not proven blocked SHALL be reported as REPORT_RESTORE_RISK.

#### Scenario: Enabled connector
- **WHEN** a connector subscription for the subject is enabled at `audit_at`
- **THEN** a REPORT_ACTIVE_DATA_FLOW finding, DISABLE_DATA_FLOW remediation, and VERIFY_DATA_FLOW_DISABLED check are emitted

### Requirement: Status decision
A case SHALL be `COMPLETE` only when every linked resource has its required final state, every retained record is present with only permitted identifiers, and no data flow or restore risk is active; otherwise it SHALL be `INCOMPLETE`.

#### Scenario: Single remaining record
- **WHEN** only `account_service/account_005` is still present
- **THEN** the case is INCOMPLETE

### Requirement: Incomplete case steps
An `INCOMPLETE` case SHALL list one finding per violation or risk citing its proving `file_id`, `activity_id`, or `audit_id`; one remediation per finding; and one verification per linked resource covering its required final state, including resources needing no remediation. Remediation and verification SHALL use `evidence_id` `""`.

#### Scenario: Verification covers untouched account
- **WHEN** only `search_service/search_001` remains and `account_service/account_006` is already absent
- **THEN** verification includes VERIFY_RECORD_ABSENT for both, each with empty `evidence_id`

### Requirement: Complete case steps
A `COMPLETE` case SHALL contain only VERIFICATION steps, one per linked resource, each citing evidence that proves its state at `audit_at`.

#### Scenario: Complete with retained audit record
- **WHEN** the account is absent, an audit record is retained, and analytics is anonymized
- **THEN** steps are VERIFY_RECORD_ABSENT, VERIFY_RECORD_PRESENT, VERIFY_RECORD_ANONYMIZED, each with a non-empty `evidence_id`

### Requirement: Evidence citation rule
Each cited step SHALL cite the latest evidence file captured at or before `audit_at` that covers the resource's system and proves its observed state. Citations SHALL never reference files captured after `audit_at` or organizer-only data.

#### Scenario: Latest covering capture
- **WHEN** two snapshots cover a resource's system, captured 2026-09-02 and 2026-09-15, and `audit_at` is 2026-09-15T12:00:00Z
- **THEN** the step for that resource cites the 2026-09-15 file

#### Scenario: Different systems cite different files
- **WHEN** a case's account resource is covered by one snapshot and its analytics resource by another
- **THEN** each step cites the file covering its own system

### Requirement: Participant-only data
The system SHALL read only files under `dataset/` for predictions and SHALL NOT use hidden golden answers, hardcoded labels, or case-family shortcuts.

#### Scenario: No organizer files
- **WHEN** the pipeline runs
- **THEN** no file outside `dataset/` and `.cache/` is read for predictions

### Requirement: Secrets handling
The system SHALL read `OPENROUTER_API_KEY` from the environment only, and SHALL NOT write it to logs, caches, outputs, or reports.

#### Scenario: Missing key with warm cache
- **WHEN** the key is absent and every needed response is cached
- **THEN** the run completes using cached responses

### Requirement: Sample evaluation report
The system SHALL score `output` for `dataset/sample_deletion_requests.csv` against `dataset/sample_output.csv` and at least three participant-authored cases, writing `evaluation/evaluation_report.md` with case-level status accuracy, step-level and field-level accuracy, sequence accuracy, the custom cases, and failures found with improvements made.

#### Scenario: Report generated
- **WHEN** the evaluation command runs
- **THEN** `evaluation/evaluation_report.md` contains every required metric and section

### Requirement: Determinism check
The evaluation SHALL run the pipeline twice and report whether both outputs are byte-identical.

#### Scenario: Determinism recorded
- **WHEN** the evaluation completes
- **THEN** the report states the determinism result

### Requirement: Evaluation score
The evaluation SHALL report status, step, field, and sequence accuracy over the 32 samples, citation validity over the sample output, and determinism (two sample runs), without running the 518 evaluation requests, each on a 0-100 scale, plus a weighted headline score. The evaluation command SHALL exit with code 0 regardless of score.

#### Scenario: Headline weights
- **WHEN** the metrics are computed
- **THEN** headline = 0.25 status + 0.20 step + 0.15 field + 0.20 sequence + 0.10 citation + 0.10 determinism

#### Scenario: Citation validity definition
- **WHEN** citation validity is computed
- **THEN** it is the share of non-empty `evidence_id` values in the 518-row output that resolve to a participant-visible `file_id`, `activity_id`, or `audit_id` captured at or before the case's `audit_at`

#### Scenario: Determinism metric
- **WHEN** two runs produce byte-identical output
- **THEN** determinism is 100

#### Scenario: Score printed
- **WHEN** the evaluation command runs
- **THEN** it prints and writes to `evaluation/evaluation_report.md` every metric and the headline score

#### Scenario: Invalid citation lowers citation validity
- **WHEN** an output step cites an `evidence_id` that is unknown or captured after the case's `audit_at`
- **THEN** citation validity is below 100 and the offending case and `evidence_id` are listed

#### Scenario: Nondeterministic output
- **WHEN** the two runs produce outputs that differ by any byte
- **THEN** determinism is 0, the differing `case_id` rows are listed, and the exit code is still 0

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
