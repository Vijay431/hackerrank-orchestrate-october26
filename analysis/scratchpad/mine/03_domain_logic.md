# 03 Domain logic analysis (read-only)

Scope read: code/identity.py, code/state.py, code/policy.py, code/planner.py, code/validate_output.py; code/ingest.py, code/loader.py, code/main.py for data structures and the pipeline. Dataset facts checked: dataset/deletion_rules.csv (15 rules), dataset/system_activity.csv (4011 rows), dataset/user_audit_log.csv (306 rows: email 107, email_hash 107, phone 92, no name changes).

Pipeline (main.py:69-86): load identities/audit/activity/evidence -> build FactIndex -> intent gate (main.py:81-82) -> dedupe same-user requests (main.py:36-44) -> ActivityLinker (main.py:45-46) -> per request: link_resources -> assess -> build_steps -> serialize (main.py:49-62) -> write_rows (main.py:84). validate_output.py is standalone and is never called from main.py.

## Identity resolution (algorithm, identifiers used, history handling, time cutoff)

- Normalization: `norm_email` = strip + lower (identity.py:13-14); `norm_phone` = digits only (identity.py:17-18); `norm_value` (identity.py:21-22). Hashes are lower-cased + stripped (identity.py:50). Names are never identifiers (identity.py:4 docstring), only stored on `Subject.name` (identity.py:46, 61-62).
- Identifier set per subject: `Subject.values()` = lower(user_id) + emails + phones + hashes (identity.py:33-35). This set is what `link_resources` searches for (state.py:73-74) and what `_exposed` checks (planner.py:57-58).
- Current snapshot: emails, phones (only when digits are non-empty), hashes from `user_identities.csv` (identity.py:45-50).
- History: every `user_audit_log.csv` row with field `email`, `phone` or `email_hash` adds both old_value and new_value to that user's set (identity.py:51-58). Other field names are skipped by `target is None` (identity.py:52-53).
- Time cutoff: NONE in identity resolution. `AuditEntry.event_time` is never read in identity.py (grep confirms), and `Identity.updated_at` is unused. A historical alias that appears after `audit_at` still resolves the subject and still becomes part of the identifier set. This conflicts with the spec rule "Use only information available at or before audit_at" (problem contract 6.2).
- Lookup: `resolve_email` uses `_by_email`, built with `setdefault` over subjects in sorted user_id order (identity.py:65-68), so when two users share a historical email the lowest user_id silently wins. `user_of_value` uses `_by_value` with the same first-wins `setdefault` (identity.py:70-73, 79-81). `is_current_email` (identity.py:86-87) is dead code.
- Phones: identity phones have no minimum length (identity.py:48-49), while `extract_refs` only keeps phone digits of length >= 7 (ingest.py:121-124). A short user phone value could therefore be a key that no evidence ref matches. This is harmless today but inconsistent.
- Unknown request email: `resolve_email` returns None, and main.py:54-57 writes NOT_APPLICABLE. There is no fallback by phone or name, so a genuine deletion request sent from an unknown address is answered NOT_APPLICABLE.

## Activity stream handling (event types handled, claims vs real state, ordering/tie-breaks, data flows & restores, timezone parsing)

Event types in dataset and whether code consumes them (grep of code/ for event_type literals):
- Consumed: `DELETE_RECORD` for account_service only, with "submitted primary profile" in details (state.py:303-304); `ANONYMIZE_RECORD` (state.py:149); `REDACT_RECORD` (state.py:150-151); `DISABLE_DATA_FLOW` (state.py:152); `BLOCK_RESTORE` (state.py:153); `LINK_RESOURCE_IDENTITY` (state.py:89-93).
- Ignored entirely: SYNC_RECORD (447), UPDATE_RECORD (672), INDEX_RECORD (400), REFRESH_CACHE (284), SEND_EMAIL (368), CREATE_EXPORT (155), RETAIN_RECORD (206), CHECK_DATA_FLOW (89), CHECK_RESTORE_ACCESS (28), RESTORE_BACKUP (1), CLASSIFY_REQUEST (10).
- Consequence: active sync, index and restore paths are never derived from the activity stream. They can only come from evidence (`ACTIVE` state via planner.py:106-109, and backup archive presence via planner.py:111-121).
- Only `source_system == "deletion_worker"` events enter the linker (state.py:195; 1466 rows). `Policy action completed` in details selects the policy-action subset (state.py:197).
- Claims vs state: `reported_status` and `reported_result` are used only to filter account candidates (state.py:156 mapping `RESULTS_FOR_STATUS`, state.py:321-322). They never set resource state. `reported_at` is used only for time slots (state.py:204-205, 223-224, 297, 319). `requested_at` is used only for the stale-absence filter (state.py:76).
- Time filters: LINK_RESOURCE_IDENTITY events are skipped if after cutoff (state.py:86-88). `in_slot` requires `event_time <= audit_at` (state.py:207). Narrative events require it (state.py:298). Account candidates require it (state.py:320).
- Gaps in the time filters: the account ownership pass `have` (state.py:307-313) has NO audit filter. Linker results are copied to links with no time check (state.py:94-96, 360-361). `planner.assess` then falls back to `link.activity_ids[0]` as evidence when no observation exists (planner.py:79). That can cite an activity_id whose event_time is after audit_at.
- Ownership of linker events uses all evidence with no time cutoff: `owners_map` iterates every fact (state.py:364-373). Later-captured evidence can therefore attribute a resource to a subject for an earlier audit.
- Ordering and tie-breaks:
  - Greedy resolution: candidate case order is `sorted(cand, key=(len(options), reported_at, case_id))` (state.py:333), then fallback is earliest free event (state.py:341-345).
  - Equal-count pairing zips events sorted by time with case ids sorted as strings (state.py:279-291, zip at 290). Assignment is deterministic but arbitrary; it can silently mis-assign events between cases.
  - Account first-action rule uses `min(nxt)`, which is the earliest linked action overall, not the next one after the account step (state.py:325-328).
- Timezone parsing: no timezone conversion anywhere. `_t` is `datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")` (state.py:22-23), so the literal Z is the only accepted zone and any other format raises an uncaught ValueError. `_mins` (state.py:160-161) and `_gap_phase` (state.py:167-169, uses `int(seconds) % 60`) depend on this.
- Most other comparisons are plain string comparisons of timestamps: state.py:76-77, 87, 124, 129, 132, 207, 298, 320, 325; planner.py:74-75, 77, 89. These are correct only if every timestamp is identical `YYYY-MM-DDTHH:MM:SSZ`. SQL header captured-at (ingest.py:157, 186) and handover timestamps (ingest.py:329-336) are not normalized.
- Retention dates: `_parse_date` (planner.py:42-51) accepts `YYYY-MM-DD...` by slicing and `%d %b %Y` (English month abbreviations only).

## Evidence matching (how evidence is linked to subject; replica drift; captured_at <= audit_at filter)

- Link by identifier: `link_resources` step 1 looks up every identity value in `FactIndex.by_ref` (state.py:71-79). A fact links its resource if `f.resource_id` is set and `f.observed_at <= cutoff`. Facts that are ABSENT or NOT_FOUND and observed before `requested_at` are dropped as stale (state.py:76).
- Inconsistency: step 1 checks `observed_at` but NOT `captured_at` (state.py:77). `observe` (state.py:124) and `assess` (planner.py:73-75) check captured_at. A resource can therefore be linked by a fact that is later ignored, which leaves it with no observation.
- Derived links: step 2 follows `*source_resource_id` attributes one hop (state.py:81-84), used for search documents pointing to their source account.
- Catalog links: step 3 (state.py:85-93) matches LINK_RESOURCE_IDENTITY details with substring `v in low`, where v is an email or a user_ id (state.py:91). This is substring matching, so `user_1` would also match inside `user_12`, and one email can match a longer email. A link only counts if the resource already has facts (state.py:92).
- Account convention: step 4 (state.py:97-106) maps `user_NN` (1-2 digits only, state.py:101) to `account_NNN` (state.py:102) only when no account_service resource is linked yet, and keeps it only if the account snapshot proves absence (`by_omission`). This is a dataset-observed convention ("account ids mirror the user number", comment at state.py:97-98), not a rule from the spec. It is the most dataset-specific heuristic in scope.
- Log trace linking: `ingest_log` copies identifiers across all records sharing a trace_id (ingest.py:304-318). One trace that spans two subjects would contaminate both.
- Replica drift and stores: `SourceInfo.store` is the file stem minus its trailing date (ingest.py:91-94). `observe` keeps one observation per store (state.py:117-143). A resource is present if ANY store holds a present observation (state.py:138-139). A stale replica snapshot therefore keeps a resource "present" even if a later primary snapshot shows it absent, as long as the replica was observed before audit_at.
- Same-file replicas: `ingest_sql` computes a table-level `store` (ingest.py:175), but `Fact.store` (ingest.py:194) is never read. Because `observe` uses the file-level `info.store` (state.py:127, 134), primary and replica tables inside one SQL file share one store and compete on the key `(observed_at, 1, captured_at)` (state.py:127). Ties are broken by first-offered wins, because `offer` only replaces on a strictly greater key (state.py:119-121). Tables are iterated in name order (ingest.py:167, 172). `customer_profiles_failover_replica` sorts before `customer_profiles_primary`, so the replica's observation can beat the primary when they tie. This needs confirming on a real SQL file that contains both tables.
- captured_at <= audit_at filter: applied in `observe` to facts (state.py:124) and to snapshots (state.py:129). Applied in `assess` to the category facts (planner.py:73-74), with a fallback to observed-only facts when none qualify (planner.py:74-75). A later-captured fact can therefore set the category.
- Snapshots from SQL: `ingest_sql` makes a Snap per coverage system holding that file's resource ids (ingest.py:199-201). A resource missing from any such snapshot is treated as absent (state.py:132). JSON `snapshots` with empty records produce an empty Snap that omits everything (ingest.py:221-222).
- Evidence skipped silently: images without a model client or cache get `info.skipped` and no facts (ingest.py:400-402, 421-422); unsupported extensions are skipped (ingest.py:443-444). Skipped files produce no facts, so their resources become false absences in `observe`.
- Non-linked evidence: finance register rows (ingest.py:376-380) and statements with NST- ids (ingest.py:381-383) produce facts that are never joined. Statement resource ids do not match RESOURCE_RE, so `system_for_resource` returns None and `link_resources` drops them (state.py:63-64).

## State reconstruction (how each resource's state at audit_at is derived; precedence rules)

- Per-fact state comes from `derive_state` (ingest.py:134-151): explicit result/state/status first, then `detector` gives IDENTIFIABLE, then http 404/200, then hit/miss, then rows count, then `enabled` gives ACTIVE or DISABLED. Anything else defaults to FOUND at every ingest site (ingest.py:195, 227, 251, 324, 348 region). A record with no status therefore counts as present.
- `observe` (state.py:110-143) reduces each store to its latest observation with `observed_at <= audit_at` and `captured_at <= audit_at` (state.py:124). A snapshot omission is an ABSENT observation with `by_omission=True` (state.py:128-135).
- Precedence in `observe`:
  1. Stores with a PRESENT state (FOUND, IDENTIFIABLE, PRESENT, ACTIVE; state.py:17) form the pool, and absent stores are used only when no store is present (state.py:138-139).
  2. Within the pool, the winner is the max of `(explicit flag, observed_at, captured_at)` (state.py:141-143). Explicit facts (flag 1) beat snapshot omissions (flag 0.5, or 0 for files with no facts). Ties go to the most recent observation.
- The `SNAPSHOT_KINDS = {"sql"}` constant (state.py:16) says omission proves absence only for complete dumps, but it is never referenced. Any SourceInfo with snaps counts, including the empty-JSON case (ingest.py:221-222). The comment and the code disagree.
- Activity is never a state source. Linked activity ids are used only as fallback evidence (planner.py:79).
- Replica-level state: a store observed as ACTIVE or FOUND keeps the resource present regardless of any absent observation elsewhere (state.py:138).

## Policy application (rule matching; tombstone; retain/redact/anonymize)

- Category resolution `Policy.category` (policy.py:33-57), in order:
  1. Facts whose `category` is a rule category or DATA_FLOW (policy.py:35-41). The first such fact in manifest order wins. `SUPPORT_MESSAGE` with a `file` attr becomes `SUPPORT_ATTACHMENT` (policy.py:38-39).
  2. `service == support_replica` or source contains `legacy_contact_index` gives SECONDARY_IDENTIFIER (policy.py:42-44).
  3. `attachment_*` events, or `file` on a support_* resource, give SUPPORT_ATTACHMENT (policy.py:45-48).
  4. `contact_lookup_completed` or `email_opt_in` give MARKETING_PROFILE (policy.py:49-50).
  5. `audience_cohort` on analytics_* gives ANALYTICS_PROFILE (policy.py:51-52).
  6. Resource prefix via PREFIX_CATEGORY (policy.py:53-55). Unknown prefixes give UNRESOLVED (policy.py:56-57).
- Rule lookup `Policy.treatment` (policy.py:59-67):
  - DATA_FLOW always maps to DISABLE, overriding any rule (policy.py:60-61).
  - BACKUP_ARCHIVE always maps to BLOCK, overriding rule_14 which says RETAIN (policy.py:62-63).
  - Otherwise an exact dict lookup on `data_category` (policy.py:30, 64-67). If the category is missing, the action is NONE and `assess` returns None (planner.py:122). That drops the resource from output silently.
- Conditions are ignored. `Rule.condition` is loaded (loader.py:57) but never evaluated. Examples from deletion_rules.csv: rule_05 SUPPORT_MESSAGE "must be retained" is always REDACT; rule_06 SUPPORT_ATTACHMENT "belongs only to the deletion subject" is always DELETE; rule_13 LEGAL_HOLD_RECORD "legal hold is active" is always RETAIN, with no expiry check; rule_14 is bypassed (see above).
- Duplicate category rows: `Policy.rules` is a dict comprehension (policy.py:30), so the last row wins silently.
- Treatment.unresolved (policy.py:25, 66) is never read. `Policy.unresolved` counts only category failures (policy.py:31, 56-57), and main.py:64-65 prints that count to stderr.
- RETAIN (planner.py:84-92): SECURITY_AUDIT_LOG flips to DELETE when a `retention_until` or `retain_until` date is on or before the audit date (planner.py:85-90). Last parsed value wins across facts (planner.py:87-88). Other RETAIN categories emit only VERIFY_RECORD_PRESENT, with no finding even when the record is missing.
- DELETE (planner.py:94-97): finding and remediation only when `present`. Otherwise VERIFY_RECORD_ABSENT only.
- REDACT and ANONYMIZE (planner.py:99-104): exposed if the observed state is IDENTIFIABLE (planner.py:100), or if present and the observed fact's refs include an identity value (planner.py:101). `_exposed` (planner.py:54-62) skips `user_` refs when `direct_only` is true, which is the case for REDACT only (planner.py:101). So ANONYMIZE treats the stable user_id as exposure, and REDACT does not.
- Tombstone: ACCOUNT_TOMBSTONE comes from the `tombstone` prefix (policy.py:12). rule_15 says REDACT (direct_only), so a tombstone is compliant when its observed fact has no email, phone or hash ref, and the user_id is allowed (planner.py:59-60).
- Gap in exposure checks: `_exposed` checks only `obs.fact.refs` (planner.py:80, 101), which contain emails, user_ ids, hashes and phone digits (ingest.py:113-125). Names are never checked, so a tombstone or support row that still holds the name is treated as compliant. Phones in free text are not detected either, because the phone digit rule applies only to keys containing "phone" (ingest.py:121).
- DISABLE (planner.py:106-109): finding only if observed state is ACTIVE.
- BLOCK (planner.py:111-121): restore_allowed, else eligible and not deletion_block, else a found archive counts as restorable. The fallback uses PRESENT_STATES, so FOUND counts. Only the observation's fact is consulted for flags (planner.py:80, 113).

## Step planning (finding order, remediation order, verification generation, evidence_id choice, COMPLETE-case verification)

- Items: one `Item` per linked resource (planner.py:33-39, built in main.py:59-60). `build_steps` returns status and steps (planner.py:125-148).
- Status: INCOMPLETE if any item has a finding, COMPLETE otherwise (planner.py:127, 138, 142).
- Finding order: `FINDING_RANK` (planner.py:12-13), then system_id, then resource_id (planner.py:127-128). Resource ids sort as plain strings, so `account_10` comes before `account_2`.
- Remediation order: `REMEDIATION_RANK` (planner.py:14-15), then system_id, then resource_id (planner.py:129-130). Ordering is global by operation type only. The spec's dependency rule (process downstream copies before sources, planner has no graph) is not implemented.
- Verification order: all items, sorted by `VERIFICATION_RANK`, then system, then resource (planner.py:131). Verification steps are emitted for compliant items too (planner.py:97, 92, 109, 121).
- Evidence choice (planner.py:79): `obs.source_id` if an observation exists, otherwise the first linked activity id (`link.activity_ids[0]`), otherwise "". Findings take this value (planner.py:143). Snapshot-omission observations use the snapshot file id as source (state.py:135).
- Remediation and INCOMPLETE verification always get `evidence_id=""` (planner.py:145, 147).
- COMPLETE: only verification steps, and they carry the item's evidence_id (planner.py:138-141). If there are no items at all, the output is COMPLETE with `[]` (vacuous). A COMPLETE step with no observation and no activity gets evidence "".
- step_no is sequential from 1 (planner.py:134-136). `serialize` uses sort_keys, compact separators and ensure_ascii=False (planner.py:151-152).

## Output validation

- validate_output.py:28-70 checks: header (line 32), case id set equality and sort (lines 36-39), status values (42-43), valid JSON (45-48), NOT_APPLICABLE must be [] (49-50), exact step field set (53-54), consecutive step_no (56-57), allowed phase/operation/state triples (58-59), phase order (61-64), empty evidence_id for REMEDIATION (65-67), COMPLETE contains only VERIFICATION steps (68-69).
- Not checked: findings have non-empty evidence_id; COMPLETE verification has non-empty evidence_id; INCOMPLETE contains at least one FINDING; INCOMPLETE verification evidence is empty (only remediation is checked, line 66); evidence ids exist in the manifest or are not after audit_at; each finding has matching remediation and verification; ordering within phases (rank order); steps is a list (line 45-52 would iterate a dict's keys); step value types; duplicate case ids (the set comparison at line 38 would catch duplicates only indirectly).
- main.py never calls the validator (main.py:83-86). It is a standalone script (validate_output.py:3).

## Edge cases explicitly handled (every special case/heuristic with file:line)

- Non-deletion intent: NOT_APPLICABLE with [] (main.py:51-52). Missing intent key defaults to False for output (main.py:51) but True for the linker universe (main.py:38). Inconsistent defaults.
- Unknown request email: NOT_APPLICABLE (main.py:54-57).
- Repeat request, same user, same reported_at and audit_at: shares linker links with the first case (main.py:39-44; alias used at main.py:59).
- Stale absence lookups before requested_at ignored: state.py:76.
- Derived source account link: state.py:81-84.
- Catalog link substring match: state.py:89-93.
- Account convention user_NN to account_NNN, 1-2 digits only, snapshot proof required, first match only: state.py:97-106.
- Account step candidate selection: window state.py:155, reported_result filter state.py:322 (with fallback to all options when empty), gap-phase filter state.py:324-328 (with fallback), greedy and fallback assignment state.py:330-345, first-action pairing 41 s offset state.py:173, 349-358.
- Chain propagation: constants state.py:164, 176-178 (state.py:178 comment says gaps "cluster at 390 s and 449 s", i.e. fitted to observed timing), loop state.py:242-278, `too_close` state.py:228-231.
- Equal-count pairing with arbitrary case order: state.py:279-291.
- Narrative "Target resource:" events matched with a 40-minute window: state.py:293-300. Writes only `by_case`, not `owner_case` (state.py:300).
- Replica preference and tie-breaks: state.py:117-143; file-level store key ingest.py:91-94.
- Snapshot omission ranking: state.py:134 (0.5 for files with facts, 0 otherwise).
- Empty JSON extract as total omission: ingest.py:221-222.
- Images: unavailable without a client, skipped (ingest.py:400-402); screenshot with no ids skipped (ingest.py:421-422); panel refs shared across tiles (ingest.py:407-413); state words (ingest.py:390-391).
- Log lines: `_started` events dropped (ingest.py:314-315); `null` resource ids dropped (ingest.py:311); trace-id reference sharing (ingest.py:304-318).
- Retention extraction from PDFs: ingest.py:367-368; finance register and NST statements: ingest.py:376-383, never linked (state.py:63-64).
- Support attachments: policy.py:38-39, 45-48; `file` flag from PDF text ingest.py:371-373.
- Category priority and fallbacks: policy.py:35-57; observed-only fallback planner.py:73-75.
- DATA_FLOW and BACKUP overrides: policy.py:60-63.
- Tombstone via REDACT with direct_only: planner.py:59-60, 99-101; rule_15.
- ANONYMIZE counts user_ refs as exposure: planner.py:101 (direct_only False).
- SECURITY_AUDIT_LOG retention to DELETE: planner.py:84-91; `_parse_date` planner.py:42-51.
- Unresolved category silently dropped: policy.py:56-57, planner.py:122.
- Zero-item COMPLETE: planner.py:138-141.
- Activity paths that bypass the audit cutoff: state.py:307-313 (no filter), state.py:94-96 and planner.py:79.

## Notable ideas

1. Enforce `audit_at` in identity: filter `user_audit_log` rows by `event_time <= audit_at` before building the alias sets (identity.py:51-58). Also filter `owners_map` facts by `captured_at <= audit_at` (state.py:364-373). Both are direct spec-compliance fixes.
2. Add the `audit_at` filter to the account ownership pass (state.py:307-313) and make `link_resources` drop linked activity ids after audit_at before they can be used as evidence (state.py:94-96, planner.py:79).
3. Make `observe` store-aware using `Fact.store` (ingest.py:175, 194) instead of the file stem (state.py:127, 134), so primary and replica tables in one SQL file are compared properly. Break ties by an explicit rule, not by first-offered order (state.py:119-121).
4. Evaluate `Rule.condition` for at least SUPPORT_MESSAGE (shared context), SUPPORT_ATTACHMENT (sole subject) and LEGAL_HOLD_RECORD (hold still active at audit_at) instead of the constant action mapping (policy.py:59-67).
5. Let rule_14 (BACKUP_ARCHIVE RETAIN) apply when the restore is blocked, instead of the unconditional BLOCK override (policy.py:62-63), and check that BLOCK still fires where the spec says so.
6. Add name detection to the exposure check (planner.py:54-62). Name values can come from the current snapshot and audit history (identity.py:46), which is the only source of names the code already has.
7. Build a dependency order for remediation: downstream copies (search, analytics, exports, support) before source account rows, and DISABLE/BLOCK before any deletion that could be recreated (planner.py:14-15, 129-130). The current global rank does not do this.
8. Strengthen `validate_output.py` with the missing checks listed above and call it from main.py after write_rows (main.py:83-86). Require non-empty evidence for findings and COMPLETE verification, and require at least one FINDING for INCOMPLETE.
9. Surface silent drops: count and log resources whose `treatment` is NONE (planner.py:122), skipped evidence files (ingest.py:400-402, 443-444), and UNRESOLVED categories beyond the stderr count (main.py:64-65).
10. Document or remove dataset-fitted constants (state.py:164, 173, 176-178, 19-157). AGENTS.md section 6.7 forbids case-family shortcuts, so each one should be justified as a general timing rule or moved into a documented heuristic with evaluation evidence.
11. Remove dead code and unused constants: `is_current_email` (identity.py:86-87), `slot_of` (state.py:209-210), `ANCHOR_WINDOW` (state.py:19), `SNAPSHOT_KINDS` (state.py:16, but its intent is worth keeping, see above), `ISO_RE` (ingest.py:30), `RECORD_TYPE_CATEGORY` (ingest.py:54), `Treatment.unresolved` (policy.py:25).
12. Verify the claim in state.py:15 by making `observe` use `SNAPSHOT_KINDS` to decide which sources can prove omission (state.py:128-135).
13. Normalize every timestamp to `YYYY-MM-DDTHH:MM:SSZ` at ingest (ingest.py:157, 186, 329-336) so the string comparisons in state.py and planner.py stay correct.
