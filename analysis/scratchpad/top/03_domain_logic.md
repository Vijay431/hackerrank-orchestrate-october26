## Identity resolution (algorithm, what identifiers: email/phone/hash/name/user_id, history handling, time cutoff)

Base path for all refs: `/tmp/top/ghost-data-still-exists/`. Pipeline driver is `main.py` (not in scope; callers noted where seen).

- Build: `IdentityIndex.__init__` (`ghost/identity.py:32-61`). For each `user_identities.csv` row the token set is `{user_id, email, email_hash}` (lowercased) plus `tokens(phone)` (`identity.py:38-43`). It asserts `sha256(email) == email_hash` with a bare `assert` (`identity.py:41`), which disappears under `python -O`.
- Identifier types recognised by `tokens()` (`identity.py:14-29`):
  - email: `EMAIL` regex (`identity.py:8`), lowercased.
  - user_id: `USER` regex `\buser_\d+\b` (`identity.py:9`), lowercased.
  - SHA-256 hex: `HASH` regex, 64 hex chars (`identity.py:10`). Only the email hash is ever produced; no hash of phone or name.
  - phone: `PHONE` regex (`identity.py:11`), stripped to digits, kept only if 9–15 digits (`identity.py:25-28`).
  - name: NOT a token. Names appear only in `IDENTIFIER_FIELDS` used by the "has direct identifiers" heuristic (`ghost/state.py:18-20`, `:118-129`).
- Recursion: `tokens()` walks dicts and lists and scans every string value, including free text (`identity.py:16-21`). Because `observation()` sets `link_tokens = frozenset(tokens(record))` on the whole record (`ghost/evidence.py:66-74`), any record that merely mentions another person's email links to that person too. Decoys are handled later by `belongs_elsewhere` (see Activity).
- History: `user_audit_log.csv` rows are applied only when `user_id` is in the snapshot (`identity.py:45-48`). Tokens are drawn from `old_value` and `new_value` (`identity.py:49-51`). Every email-like historical token gets its SHA-256 added (`identity.py:52-53`) and `by_email[email] = uid` is set (`identity.py:54`). That `by_email` write has no collision check, so a later row silently overwrites an earlier mapping.
- Ownership collisions: after all users and history are merged, any token owned by two `uid`s raises `ValueError` and aborts the run (`identity.py:56-60`). This is a hard failure, not a warning.
- Lookup: `IdentityIndex.resolve(email)` (`identity.py:63-67`) matches the request email case-insensitively against `by_email`. It returns `(uid, full token set)`, where the set includes all historical emails and hashes. An unknown email returns `(None, set())`. The result is used as `subject` by `correlate` (`ghost/activity.py:113`) and passed as `subject_tokens` to `resources()` (`ghost/state.py:190`; caller `main.py:60`).
- Time handling in identity: `resolve` has no time cutoff. Every historical identifier is valid for the whole history. Time enters only through evidence capture windows:
  - Link window `owner_window = (requested_at - 30d, audit_at + 7d)` on `file_captured_at` (`ghost/activity.py:115-117`; `ghost/state.py:196-199`).
  - Readbacks used for state must have `file_captured_at <= audit_at` and `record_time <= audit_at` (`ghost/state.py:207-208`).

## Activity stream handling (event types handled, how claims vs real state are distinguished, ordering/tie-breaks by timestamp, data flows & restores, timezone parsing)

Event types and roles:
- `DELETE_RECORD` on `target_system == account_service` with an `account_*` resource is the only deletion candidate type (`ghost/activity.py:104-105`).
- `LINK_RESOURCE_IDENTITY` rows become link observations: `file_id = activity_id`, captured = `event_time`, `link_tokens` from `details` (`ghost/evidence.py:426-437`). These also feed PDF and screenshot alias matching (`ghost/evidence.py:318-328`, `:337-342`).
- Follow-ups: `CHECK_DATA_FLOW`, `CHECK_RESTORE_ACCESS`, or a `FOLLOWUP` regex match on details (`ghost/activity.py:16-18`, `:47-49`). Follow-ups only feed `follows_candidate` and a constraint counter (`ghost/activity.py:98-103`, `:143-144`). They never create a resource.
- Account checkpoint: `SYNC_RECORD` with "Replication worker reported its final checkpoint for account_" inside `[report-2h, report+5h]` (`ghost/activity.py:94-97`).
- Policy-action timing marks: any row whose details contain "Policy action completed for" is mapped to a fixed second-of-minute offset by `policy_offset` (`ghost/activity.py:30-44`). Details in §Notable.
- Worker class: `worker_operation_class` maps support/analytics worker ops to categories (`ghost/state.py:59-76`).

Claims versus real state:
- Activity rows are used for ownership and timing only. The `record_from_action` docstring says so: "state only from independent readback" (`ghost/state.py:79-89`). `account_state_from_id` also infers ABSENT only from omission in a later complete snapshot (`ghost/state.py:92-115`).
- `reported_status` maps to `reported_result` via `STATUS_RESULT` (`ghost/activity.py:15`). It is used only as a preference filter (`ghost/activity.py:123-125`), with fallback to all candidates. It is never state.
- Comments that disclaim proof: `earliest_activity_tiebreak` "does not prove ownership" (`ghost/activity.py:53`), and `unique_action_target` (`ghost/activity.py:66-76`).
- `data_flow` and restore state are never taken from activity rows. They come only from evidence observations classed `DATA_FLOW` or `BACKUP_ARCHIVE` (`ghost/state.py:149-162`).

Ordering and tie-breaks:
- Candidate delete window: `[report-2h, report+15m]` (`ghost/activity.py:121-122`). Narrow window: `[report-80m, report-40m]` (`:126-128`). If the narrow window is empty, all candidates are used (`:128`).
- Fixed-point assignment loop (`ghost/activity.py:157-193`):
  - Cases are processed in order of `(len(candidates), case_id)` (`:162`), i.e. fewest candidates first.
  - Identity match wins if exactly one open candidate has `("account_service", rid)` in the linked set (`:166-171`).
  - Otherwise survivors must satisfy every constraint offset within 0.75s and pass `follows_candidate` (`:172-174`).
  - A single open candidate is accepted even if constraints fail (`:175-177`).
  - Same-evidence scoring: if the top score is unique and positive, it wins (`:178-184`).
  - The loop repeats until no change (`:160-193`).
- Ambiguous leftovers: each unassigned case gets `earliest_activity_tiebreak` = `min(event_time, activity_id)` (`:52-54`, `:195-207`). Tie-break assignments are flagged only in `ambiguous` and `counts`, not in the output.
- Policy-row attachment: per proposed policy row the tie-break is `min((distance, |event_time - report|, cid))` (`:227-231`). One row attaches to at most one case.
- Decoy exclusion: `belongs_elsewhere` (`:149-155`) excludes a candidate when evidence in the owner window has exactly one owner and that owner is not this subject.
- Explicit subject links beat batch time: if the case is explicitly linked in the same `target_system` to a different resource, the policy row is skipped (`:221-224`).
- Shared-batch guard: `unique_action_target` returns None if another request was reported within 900s (`:69-70`). Its worker-action candidates use a ±900s window (`:72-73`).

Data flows and restores:
- Activity cannot add a flow or restore. Those come from evidence states (`ghost/state.py:149-162`), and only for linked resources.
- DATA_FLOW state: first of `enabled`, `delivering`, `active` present, truthy gives ACTIVE, otherwise DISABLED (`ghost/state.py:149-153`). No key gives UNKNOWN.
- BACKUP_ARCHIVE state: `decision == deny` or `deletion_block` true gives BLOCKED (`:155-156`). Then `restore_allowed`/`eligible` (`:157-159`). A listed image archive with no block gives ACTIVE (`:160-162`).

Timezone parsing:
- `at()` (`ghost/activity.py:21-22`) replaces a trailing `Z` with `+00:00` and calls `fromisoformat`. No explicit conversion to UTC is done. Aware datetimes compare correctly across offsets.
- A naive timestamp (no offset) raises `TypeError` when compared with an aware one. There is no guard.
- `state.time()` (`ghost/state.py:24-25`) uses the same convention. The log regex `TIME` requires a literal `Z` suffix (`ghost/evidence.py:23`), so other log timestamps are rejected (`_log_line`, `:203-208`) and counted as malformed.
- Second-of-minute arithmetic uses `.second` of the parsed value (`ghost/activity.py:102`, `:142`, `:173`, `:213`, `:225`). This is only correct if offsets are whole minutes, which holds for any real timezone offset.

## Evidence parsing (per format: SQL via sqlite? JSON, logs, txt, PDF, images; matching to subject; replica drift; captured_at <= audit_at filter)

Dispatch: `load()` (`ghost/evidence.py:378-423`) reads `evidence_files.csv` (`:381`). `file_path` is relative to the dataset root (`:386`). Suffix decides the parser (`:388-414`). Unknown suffixes contribute nothing (`:412-413`). The loader does NOT filter by `captured_at` against `audit_at`. That filter is applied downstream (see State reconstruction).

- JSON, `json_observations` (`ghost/evidence.py:89-134`). Three shapes:
  - `snapshots` (`:100-108`): one `scope` observation per snapshot (system from `data_store`, collection, `captured_at`), then each record.
  - `service_exports` (`:109-126`): system → collection → records. `index_queries` hits are flattened (`:116-123`). A query with no hits but a `resource_id` is kept as a record (`:121-123`).
  - `records` (`:127-133`): system from the record or `obj.source`/`origin`. Time from `recorded_at`, `observed_at`, `captured_at`, `exported_at`, then capture time.
  - `unpack_record` (`:77-86`) parses a `record_json` string and merges it over the top-level keys, so nested keys win.
- SQL, `sql_observations` (`ghost/evidence.py:137-181`). Uses Python `sqlite3` in memory, not the CLI. `executescript` runs the whole file (`:153`) under an authorizer (`:142-152`) that allows only `PRAGMA foreign_keys=ON`, denies ATTACH/DETACH, and allows only the `json_valid` function. Table names must match `[A-Za-z_][A-Za-z_0-9]*` (`:157`).
  - `snapshot_scope` rows become scope observations keyed on `origin_system`, `system_id`, `data_store`, or `system` (`:160-164`).
  - A `customer_data_*` table with a `record_json` column yields an extra full-copy scope for `account_service` (`:167-171`). This is what allows absence inference even when the table has zero account rows.
  - System for each row: `origin_system`, then `system_id`, then `system_of_table` (`:37-45`), then `system_of(resource_id)`. `record_time` is `updated_at` (`:175-177`).
- Log, `log_observations` (`ghost/evidence.py:238-285`) and `_log_line` (`:203-235`). Accepts four envelopes:
  - JSON body (`:209-213`).
  - `key=value` pairs via `shlex` (`:184-200`), with numeric, null, and boolean coercion (`:195-196`). A nested `message` containing `event=` is re-parsed (`:198-199`).
  - Pipe-delimited, 5 or more columns → service, trace_id, event (`:216-220`).
  - Bracket format `[LEVEL] [service] [trace] event:` (`:221-223`).
  - `<...>` lines with trace IDs `tr-`/`rb-`/`rp-` via `TRACE` (`:224-227`). `requestId` starting with `tr-` or `rb-` is also a trace (`:233-234`).
  - Lines are grouped by `trace_id` (`:249-253`). Trace-less lines with a `resource_id` become singletons. Anything else is dropped.
  - Subject tokens come from `lookup_key`, `match_key`, `subject_key`, `scan_key`, `correlation_key`, `subject_ref`, `subject_reference`, `matched_value`, `contact_query`, `owner_key`, `recipient_key`, `contact_key`, `query_key` (`:258-262`). They are unioned into the link tokens of EVERY resource in that trace group (`:282-284`). This is group-wide linkage.
  - Within a group, later lines overwrite earlier fields (`:265-273`). Exception: a `cache_lookup` `result` with no `resource_id` is not inherited (`:270-272`).
  - `_replica` source systems are remapped to `system_of(rid)` (`:277-278`).
  - Malformed lines are counted and warned, not fatal (`:241-244`).
- Text, `text_observations` (`ghost/evidence.py:288-298`). Exactly six pipe columns with a leading timestamp. A leading `- ` bullet is stripped. Fields become `record_type`, `result`, `subject_reference`.
- PDF, `pdf_observations` (`ghost/evidence.py:301-332`). Uses `pypdf`.
  - Resource IDs are matched per line with `RESOURCE` (`:311`). If the whole document has exactly one unique resource, the context is the whole document (`:312`). Otherwise it is the line.
  - Alias linkage: a parenthesised alias in an activity link's `details` that appears as a whole token in the document text attaches that link's resource, provided the resource is not already named in the document (`:318-328`).
  - Fallback: if nothing matched, a scope observation with the first 2000 characters (`:329-331`).
- Images, `vision_observations` (`ghost/evidence.py:335-358`, dispatch `:399-411`). Pixels are not parsed here. The code needs a pre-reviewed transcription (`vision_records`, produced by `transcribe_all` in `main.py:35`, outside scope).
  - A visible ID is accepted if it fully matches `RESOURCE`. Otherwise it is mapped through the link alias table, lowercased (`:337-346`).
  - `backup_*` IDs set `image_archive_listed = True` (`:352-353`), which `state()` turns into ACTIVE (`ghost/state.py:160-162`).
  - Without a transcription the file gets zero coverage and a warning (`:400-403`).
  - Optional Tesseract cross-check, `image_crosscheck` (`:361-375`), only warns when a reviewed ID is missing from OCR. It adds no facts (`:407-411`).
- Failure policy (`ghost/evidence.py:415-422`): unreadable JSON or log files give zero coverage and a warning. Unreadable SQL, text, PDF, or PNG raise `RuntimeError` and abort.
- Matching to a subject: `link_tokens` is intersected with the subject token set. Used in `resources` (`ghost/state.py:196`), `correlate` (`ghost/activity.py:116-120`), and `belongs_elsewhere` (`ghost/activity.py:149-155`).
- Replica drift: `physical_scope` (`ghost/state.py:177-187`) keeps tables containing `replica` or `primary` as separate physical copies. Snapshot scopes group by system and collection. Within each copy the latest observation by `(record_time, file_captured_at)` wins (`ghost/state.py:225-230`). The resulting decision is then the latest non-ABSENT copy if any exists, so a surviving replica dominates (`ghost/state.py:232-233`). Output collapses to one `(system, rid)` decision (`ghost/state.py:236`), so per-replica remediation steps are never emitted.
- `captured_at <= audit_at` filter: applied in `resources` (`ghost/state.py:207-208`), `account_state_from_id` (`:96-97`), and `record_from_action` (`:82-83`). Two explicit rules:
  - A resource seen only in evidence captured after audit is dropped entirely, unless its category is SECURITY_AUDIT_LOG or LEGAL_HOLD_RECORD (`ghost/state.py:210-213`).
  - A retained-category resource with no valid readback becomes a gap and an unresolved entry (`:214-216`).

## State reconstruction (how each resource's state at audit_at is derived; precedence rules)

`resources()` (`ghost/state.py:190-237`), in order:
1. Linked set: `(system, rid)` pairs where `link_tokens` intersect subject tokens and `file_captured_at` lies in `[requested_at-30d, audit_at+7d]` (`:195-201`).
2. Valid readbacks: same system and rid, `kind == "record"`, `file_captured_at <= audit`, `record_time <= audit` (`:207-208`). None means gap and unresolved, unless the late-only exception applies (`:209-216`).
3. Category: priority `SUPPORT_ATTACHMENT` > `MARKETING_PROFILE` > `SECONDARY_IDENTIFIER` > last valid (`:218-220`). `worker_operation_class` overrides it when a worker op is unambiguous (`:221`).
4. Physical-copy dedupe: latest per `physical_scope` by `(record_time, file_captured_at)` (`:225-230`).
5. Per-copy state via `state(obs, cat)` (`:231`). Chosen: latest non-ABSENT copy if any, else latest overall (`:232-233`). UNKNOWN adds a gap but still produces a decision (`:234-236`).

`state()` precedence (`ghost/state.py:132-174`):
- a. `result` in `{NOT_FOUND, ABSENT, MISS, DELETED}`, or `status_code`/`http_status` 404 → ABSENT (`:134-136`).
- b. `profile` key present and None → ABSENT (`:137-138`).
- c. `rows == "0"`, or `index_queries` with `total == 0` or no documents → ABSENT (`:139-141`).
- d. Explicit `result` in `{FOUND, PRESENT, IDENTIFIABLE, ANONYMIZED, REDACTED, ACTIVE, DISABLED, BLOCKED}` (`:142-148`). It is returned verbatim, except `FOUND`, which depends on category (`:143-147`). Support, tombstone, email-log, analytics, and telemetry categories become IDENTIFIABLE or REDACTED/ANONYMIZED depending on `has_direct_identifiers`. Other categories become PRESENT.
- e. DATA_FLOW keys `enabled`, `delivering`, `active` (`:149-153`).
- f. BACKUP_ARCHIVE: `deny` or `deletion_block` → BLOCKED, then `restore_allowed`/`eligible`, then `image_archive_listed` → ACTIVE, else UNKNOWN (`:154-163`).
- g. USER_EXPORT with `download_available` or `available` False → ABSENT (`:164-165`).
- h. USER_PROFILE with `account_status == DELETED` → ABSENT (`:166-167`).
- i. Analytics/telemetry → IDENTIFIABLE if identifiers, else ANONYMIZED (`:168-169`).
- j. Support/tombstone/email-log → IDENTIFIABLE if identifiers, else REDACTED (`:170-171`).
- k. Any other non-empty category → PRESENT; empty category → UNKNOWN (`:172-174`).

`has_direct_identifiers` (`:118-129`): an integer `direct_identifiers` field wins. Otherwise any non-empty identifier field not equal to `[REDACTED]` counts. `message_text` containing `@` also counts.

Category resolution (`ghost/state.py:38-56`): a declared `record_type` in `PREFIX_CATEGORY` values wins (`:40-42`). Otherwise the prefix map (`:11-17`, `:43-45`). For SUPPORT_MESSAGE, text containing "contact" without "attachment" becomes SECONDARY_IDENTIFIER (`:48-50`). "attachment", "uploaded", "object_storage", or ".pdf" makes it SUPPORT_ATTACHMENT (`:51-52`). Analytics text with "contact", "marketing", "opt_in", or an `email_opt_in` field becomes MARKETING_PROFILE (`:53-55`). The text heuristic scans `event`, `collection`, `table`, `file_name`, `file`, `source`, `text`.

Account absence, `account_state_from_id` (`ghost/state.py:92-115`): if no valid readback exists, the latest full account snapshot in `[reported_at, audit_at]` is used (`:103-109`). If the record is missing from it, an ABSENT observation is synthesised with `result: NOT_FOUND` (`:110-115`). This requires a snapshot captured after the report.

Action-target readback, `record_from_action` (`ghost/state.py:79-89`): for a unique target from `unique_action_target`, it uses the latest valid readback by `(record_time, file_captured_at)`.

## Policy application (how rules are matched: category/condition; tombstone handling; retain/redact/anonymize)

- Hard-coded table: `RULE_ACTION` (`ghost/policy.py:8-15`). `load_rules` (`:18-24`) compares each CSV row's `required_action` with it and raises `ValueError` on any mismatch. It returns rows keyed by `data_category`.
- Matching: only `data_category` membership is used. The `condition` column is never read by any code in scope (the grep found no reference). Conditions are approximated by state branches and by notes (`ghost/policy.py:66-67`, `:72-75`).
- `treatment()` (`ghost/policy.py:27-77`) returns `(finding, remediation, verification, note)`:
  - Category not in rules → `"category absent from policy"` (`:29-30`). `DATA_FLOW` is exempt from this check (`:29`).
  - `current == UNKNOWN` → `"state unsupported"` and no steps (`:31-32`).
  - Delete group, `{USER_PROFILE, SECONDARY_IDENTIFIER, SEARCH_INDEX_ENTRY, CACHE_ENTRY, SUPPORT_ATTACHMENT, USER_EXPORT, MARKETING_PROFILE}` (`:34-40`): finding and DELETE_RECORD when not ABSENT, always VERIFY_RECORD_ABSENT.
  - Redact group, `{SUPPORT_MESSAGE, ACCOUNT_TOMBSTONE, EMAIL_DELIVERY_LOG}` (`:41-51`): ABSENT gives verification only (`:42-43`). Otherwise finding `REPORT_EXPOSED_PII` and REDACT_RECORD unless state is REDACTED (`:48-50`). Always VERIFY_RECORD_REDACTED.
  - Anonymize group, `{ANALYTICS_PROFILE, PRODUCT_TELEMETRY}` (`:52-58`): exposed unless ANONYMIZED or ABSENT (`:55`). Always VERIFY_RECORD_ANONYMIZED.
  - DATA_FLOW (`:59-63`): ACTIVE gives finding and DISABLE_DATA_FLOW. VERIFY_DATA_FLOW_DISABLED is always emitted.
  - BACKUP_ARCHIVE (`:64-70`): ACTIVE gives REPORT_RESTORE_RISK and BLOCK_RESTORE. VERIFY_RESTORE_BLOCKED is always emitted.
  - SECURITY_AUDIT_LOG and LEGAL_HOLD_RECORD (`:71-76`): never a finding or remediation. Always VERIFY_RECORD_PRESENT, even if state is ABSENT.
- Tombstones (`ghost/policy.py:41`, `:46-47`, `:51`): treated as REDACT, not DELETE, which matches the spec. Two gaps:
  - ABSENT tombstone yields VERIFY_RECORD_ABSENT (`:42-43`). The spec wants the stable reference retained, so a missing tombstone should be a finding or a VERIFY_RECORD_PRESENT, not a pass.
  - No field-level check that the stable `user_id` survives. The note "stable reference retention assumed from category" (`:47`) only goes to gaps.
- Notes (`:36-37`, `:45`, `:47`, `:67`, `:73`, `:75`) go to the gaps list only (`ghost/planner.py:48-49`). They never change status.
- Retained categories never get DELETE_RECORD, which is correct.

## Step planning (ordering of findings, remediation ordering — flows/restores first, downstream before source —, verification generation; evidence_id choice; COMPLETE case verification)

`plan()` (`ghost/planner.py:38-84`):
- Gate: `is_deletion_request` unless an `authorized` override is passed (`:42`). Non-deletion returns `NOT_APPLICABLE` with `[]` (`:43`).
- Per resource, in the order given by `resources()` (which is sorted by `(system, rid)`, `ghost/state.py:205`): FINDING, REMEDIATION, and VERIFICATION steps are appended from `treatment` (`:50-57`).
- `evidence_id` is `obs.file_id` for FINDING only. REMEDIATION and VERIFICATION get `""` during construction (`:57`).
- Status: INCOMPLETE iff any FINDING exists (`:58`). Gaps and notes do not affect status.
- INCOMPLETE augmentation (`:59-74`): unresolved resources without a verification step get a future VERIFICATION step with the inferred target state for their category (`:65-70`), `evidence_id = ""` (`:73`).
- COMPLETE citation (`:75-78`): every step's `evidence_id` is the `file_id` of the chosen observation for its `(system, rid)`. This is one citation per resource, not one per check.
- Canonical sort (`:79`): by `RANK[(phase, operation)]` and then `system_id`, `resource_id` as strings. `RANK` is defined at `:17-18`, operations in `OPERATIONS` at `:9-16`.
  - Order: FINDING ops, then REMEDIATION ops (DISABLE_DATA_FLOW, BLOCK_RESTORE, DELETE_RECORD, REDACT_RECORD, ANONYMIZE_RECORD), then VERIFICATION ops.
  - Consequence: flows are disabled and restores blocked before any delete or redact. That matches the spec.
  - Downstream before source is NOT implemented. There is no dependency graph. Within DELETE_RECORD the tie-break is alphabetical by `system_id`, so `account_service` sorts before `search_service`, `support_platform`, and `analytics_platform`. The account (source) is therefore deleted before its downstream copies. This contradicts AGENTS.md §6.5 ("Process downstream copies before their source records when the dependency requires it").
- `step_no` renumbered from 1 (`:80-81`).
- COMPLETE verification: only VERIFICATION steps remain, since COMPLETE requires no FINDING. A COMPLETE row keeps verification for every resource that has a valid, non-unknown state. Resources with no valid state are dropped silently for COMPLETE (they are only added for INCOMPLETE, `:59`).
- Empty output: if there are no steps, a gap is recorded (`:82-83`), but status is still COMPLETE with `steps_json = []`. `validate.py:56-57` flags this as invalid. No guard exists here.
- Unknown-state risk: a resource with UNKNOWN state yields no steps (`policy.py:31-32`) and does not block COMPLETE, because COMPLETE depends only on the absence of FINDING steps (`planner.py:58`). The `gaps` list is not consulted for status. This is a silent-COMPLETE path. Whether `main.py:79+` handles it is outside scope; not verified.

## Output validation

`validate()` (`ghost/validate.py:33-88`) is a mechanical contract check:
- Coverage: row count and case_id multiset equal to the request file (`:36-39`). Rows sorted by case_id (`:40-41`).
- Status enum (`:49-50`). NOT_APPLICABLE must have no steps (`:54-55`). Other statuses must have steps (`:56-57`).
- INCOMPLETE must contain all three phases (`:58-59`). COMPLETE must contain only VERIFICATION steps (`:60-61`).
- Step schema: exactly the seven fields (`:64`), `step_no` an int and sequential (`:65`), other fields strings (`:66`).
- `(phase, operation)` legal in `RANK`, and `state` equals `STATES[operation]` (`:70-73`). `STATES` is at `ghost/validate.py:22-30`.
- Citation presence: required iff phase is FINDING or the case is COMPLETE (`:74-77`).
- Citation existence: in the evidence manifest or as an activity_id (`:43-44`, `:78-84`).
- Citation time: `captured_at <= audit_at` (`:78-82`). Equality passes.
- Canonical order: must equal the planner's sort (`:85-87`).
- `main()` (`:91-112`) parses `steps_json` with `json.loads` and runs `validate`. It is also used as a per-case self-check in `ghost/agent_tools.py:357`.

Not checked (gaps in validation):
- That citations actually support the claim.
- That every FINDING has a matching REMEDIATION.
- That `resource_id` exists in the data or matches the category.
- That `system_id` is consistent with the category.
- That COMPLETE cases have a verification for each linked resource.
- That steps are not duplicated.

## Edge cases explicitly handled (list every special case/heuristic you find with file:line)

1. Historical email in audit log: token and SHA-256 added (`ghost/identity.py:45-55`).
2. Audit rows for unknown users skipped (`identity.py:47-48`).
3. Identifier shared by two users aborts the run (`identity.py:56-60`).
4. Phone accepted only at 9–15 digits (`identity.py:25-28`).
5. Non-deletion requests, including negated phrasing (`ghost/planner.py:21-35`). Negative patterns `:24-29`, positive keywords `:32-34`.
6. Non-deletion → NOT_APPLICABLE with no steps (`planner.py:42-43`).
7. Nested `record_json` merged, nested keys override (`ghost/evidence.py:77-86`).
8. Snapshot scope markers (`evidence.py:100-108`, `:105-106`, `:160-164`).
9. Full-copy SQL table allows absence inference (`evidence.py:167-171`; `ghost/state.py:103-115`).
10. Full snapshot must be captured at or after report (`ghost/state.py:103-106`).
11. Empty `index_queries` hits treated as ABSENT (`evidence.py:116-123`; `state.py:139-141`).
12. Cache-lookup miss result not inherited into a later readback (`evidence.py:270-272`).
13. `_replica` source remapped to canonical system (`evidence.py:277-278`).
14. Malformed log lines warned, not fatal (`evidence.py:241-244`).
15. Unreadable JSON or log gives zero coverage; other formats abort (`evidence.py:416-422`).
16. Unknown file suffixes ignored (`evidence.py:412-413`).
17. Screenshot without transcription gives zero coverage (`evidence.py:400-403`).
18. Listed backup image → ACTIVE restore risk (`evidence.py:352-353`; `state.py:160-162`).
19. Optional OCR cross-check only warns (`evidence.py:361-375`, `:407-411`).
20. PDF whole-document context when a single resource is named (`evidence.py:312`).
21. PDF alias linking via link details (`evidence.py:318-328`).
22. PDF fallback scope record (`evidence.py:329-331`).
23. Pipe-delimited text rows with bullet stripping (`evidence.py:288-298`).
24. Replicas and primaries kept separate (`state.py:179-183`).
25. Latest non-ABSENT copy wins over ABSENT (`state.py:232-233`).
26. Late-only evidence ignored for non-retained categories (`state.py:210-213`).
27. Retained categories with no readback become gaps (`state.py:214-216`).
28. Worker op overrides category when unambiguous (`state.py:59-76`, `:221`).
29. `FOUND` depends on category and identifiers (`state.py:143-147`).
30. Status results 404, NOT_FOUND, MISS, DELETED → ABSENT (`state.py:134-136`).
31. `profile` key present but None → ABSENT (`state.py:137-138`).
32. `rows == "0"` → ABSENT (`state.py:139`).
33. USER_EXPORT unavailable → ABSENT (`state.py:164-165`).
34. USER_PROFILE DELETED → ABSENT (`state.py:166-167`).
35. Email/hash/name identifiers including `[REDACTED]` markers ignored (`state.py:118-129`).
36. Shared-batch guard ±900s (`activity.py:66-76`).
37. Fewest-candidates-first assignment order (`activity.py:162`).
38. Identity-match preference (`activity.py:166-171`).
39. Constraint ±0.75s tolerance (`activity.py:173`, `:226`).
40. Single-candidate override when constraints fail (`activity.py:175-177`).
41. Same-evidence scoring tie-break (`activity.py:178-184`).
42. Ambiguous cases tie-broken by earliest time then activity_id (`activity.py:52-54`, `:195-207`).
43. Decoy exclusion via unique foreign owner (`activity.py:149-155`).
44. Explicit subject link outranks batch time (`activity.py:221-224`).
45. Policy row attached to at most one case (`activity.py:227-231`).
46. Policy tie-break by distance, then time delta, then case_id (`activity.py:227-231`).
47. Follow-up checkpoint for this account counted (`activity.py:94-97`).
48. Category priority SUPPORT_ATTACHMENT > MARKETING_PROFILE > SECONDARY_IDENTIFIER (`state.py:218-220`).
49. Declared `record_type` wins over prefix (`state.py:40-42`).
50. Text heuristics for support and analytics categories (`state.py:46-55`).
51. Policy table tamper check (`policy.py:20-23`).
52. Attachment ownership note (`policy.py:36-37`).
53. Tombstone treated as REDACT (`policy.py:41`, `:46-47`).
54. DATA_FLOW always verified (`policy.py:59-63`).
55. Backup always verified blocked (`policy.py:64-70`).
56. Retained categories always verified present (`policy.py:71-76`).
57. Unknown state yields no steps (`policy.py:31-32`; `state.py:234-235`).
58. INCOMPLETE adds verification for unresolved resources with inferred target state (`planner.py:59-74`).
59. COMPLETE citation: one file per resource (`planner.py:75-78`).
60. Canonical ordering enforced both in planner and validator (`planner.py:79`; `validate.py:85-87`).
61. Shared CSV reader strips BOM (`evidence.py:49`).
62. SQL authorizer restricts PRAGMA, ATTACH, DETACH, and functions (`evidence.py:142-152`).
63. Timing-based heuristics: policy offsets and follow-up offset (`activity.py:30-44`, `:102`).

## Notable/differentiating ideas

Strengths:
- Two-stage correlation: deletion batches are assigned to cases using candidate count, identity links, constraints, follow-ups, and shared evidence, in a fixed-point loop (`ghost/activity.py:157-193`). Each step is deterministic.
- Claims are kept separate from state. Activity rows and reported statuses only assign ownership or timing; state comes from readbacks (`state.py:79-89`, `activity.py:15`, `:53`).
- Replica-aware physical-copy selection, where any surviving copy dominates (`state.py:177-187`, `:225-233`).
- Canonical sort and output validation mirror each other, and `validate` is reused per case by the agent (`validate.py:85-87`; `agent_tools.py:357`).
- Deterministic tie-breaks throughout, with `activity_id` as the final key (`activity.py:54`, `:162`, `:227-231`).
- Policy table is cross-checked against the CSV and fails loudly on drift (`policy.py:20-23`).

Risks worth scrutinising:
- Timing fingerprint (highest risk). `policy_offset` (`ghost/activity.py:30-44`) maps action types to half-second second-of-minute offsets: 19.5, 49.5, 20.5, and 50.5. `follows_candidate` uses 51.5 (`:102`). The matcher then compares `(second + k) % 60` with the delete's second within 0.75s (`:142`, `:225-226`). This recovers linkage from the generator's timestamp pattern, not from content. It is the kind of case-family shortcut that AGENTS.md §6.7 and §7 forbid, and it is the most likely point of challenge. It also depends on timestamps being whole-second values.
- `condition` column unused. Policy matching ignores it, so rules are not evaluated as written (`ghost/policy.py:18-24`, `:27-77`).
- Downstream-before-source ordering not implemented (`ghost/planner.py:79`). See Step planning.
- Silent COMPLETE for unknown or empty cases (`ghost/planner.py:58`, `:82-83`; `policy.py:31-32`).
- Tombstone ABSENT treated as a pass (`ghost/policy.py:42-43`).
- Retained categories verified PRESENT even when absent (`ghost/policy.py:71-76`).
- Group-wide subject linkage in logs (`ghost/evidence.py:282-284`): one subject token in a trace links every resource in that trace.
- Global `tokens()` on whole records (`ghost/identity.py:14-29`, `ghost/evidence.py:72-74`) can link a third party's record to the subject if it contains the subject's email.
- Silent overwrite in `by_email` for historical emails (`ghost/identity.py:54`).
- Bare `assert` for the email-hash check (`ghost/identity.py:41`) is skipped under `-O`.
- Naive timestamps raise `TypeError` in comparisons (`ghost/activity.py:21-22`; `ghost/state.py:24-25`).
- Notes in `policy.py` and the "ambiguous reported separately" claim in `ghost/planner.py:22` do not produce any output; the ambiguity report is not implemented here.
- Screenshots depend on pre-reviewed transcriptions (`ghost/evidence.py:335-358`, `:399-411`), so image coverage is only as good as that transcription step (`main.py:35`, outside scope).
- Keyword classifier `is_deletion_request` (`ghost/planner.py:21-35`): the negative pattern `\b(?:access|download|export|correct|update|change|login|invoice|receipt) (?:my|the)\b` (`:28`) will reject an authorised deletion that also says "change the" or "export the". Positive keywords are substring matches, so `gone` and `remov` match broadly, while some non-English forms (e.g. Portuguese `apagar`) are not covered.
- Tests exist and were not read: `tests/test_ghost.py`, `tests/test_submission.py`, `tests/test_agent.py`.
