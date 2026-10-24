# Graph Report - hackerrank-orchestrate-october26  (2026-10-24)

## Corpus Check
- 100 files · ~122,999 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 40 file(s) not represented in the graph (top: .log 26, .csv 9, (none) 4)

## Summary
- 219 nodes · 307 edges · 18 communities (15 shown, 3 thin omitted)
- Extraction: 72% EXTRACTED · 28% INFERRED · 0% AMBIGUOUS · INFERRED: 87 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Trace Submission Rules
- Deletion Decision Rules
- Pipeline Architecture
- OpsX Apply/Explore
- Customer Evidence Documents
- Eval Harness and Tasks
- OpsX Archive/Sync
- OpenSpec Propose Workflow
- OpsX New/Continue
- Account Admin Screens
- Search Index Screens
- Export and Registry Screens
- OpsX Update
- Backup Restore Risk
- Marketing Profile Flow
- OpenSpec Config

## God Nodes (most connected - your core abstractions)
1. `Ghost Data Still Exists challenge` - 16 edges
2. `Change: deletion-audit-pipeline` - 11 edges
3. `agent-trace.zip submission` - 8 edges
4. `D5 State reconstruction: latest fact at or before audit_at, replica drift` - 8 edges
5. `D7 Step planning and ordering by operation rank, deterministic serialization` - 8 edges
6. `Customer Platform Shift Handover 2026-10-01` - 8 edges
7. `/opsx:apply command (Implement tasks from a change)` - 7 edges
8. `D3 Ingestion per format (SQL, JSON/log, PDF, PNG)` - 7 edges
9. `Requirement: policy treatment` - 7 edges
10. `/opsx:archive command (Archive completed change)` - 6 edges

## Surprising Connections (you probably didn't know these)
- `Requirement: step object schema` --implements--> `Step schema (7 fields)`  [INFERRED]
  openspec/changes/deletion-audit-pipeline/specs/deletion-audit/spec.md → problem_statement.md
- `Non-goals: no LLM reasoning over evidence, no second model, no golden answers` --semantically_similar_to--> `Never use organizer-only truth or golden answers`  [INFERRED] [semantically similar]
  openspec/changes/deletion-audit-pipeline/design.md → AGENTS.md
- `Support ticket CS-4827 attachment (region ap-south)` --semantically_similar_to--> `support_platform (SUPPORT_MESSAGE/ATTACHMENT)`  [INFERRED] [semantically similar]
  dataset/evidence/documents/delivery_correction_attachment.pdf → dataset/evidence/records/customer_account_handover_20261001.txt
- `Requirement: output file contract` --implements--> `output.csv contract (case_id,deletion_status,steps_json)`  [INFERRED]
  openspec/changes/deletion-audit-pipeline/specs/deletion-audit/spec.md → problem_statement.md
- `D7 Step planning and ordering by operation rank, deterministic serialization` --implements--> `Step schema (7 fields)`  [INFERRED]
  openspec/changes/deletion-audit-pipeline/design.md → problem_statement.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **OpenSpec change lifecycle commands** — claude_commands_opsx_new, claude_commands_opsx_continue, claude_commands_opsx_apply, claude_commands_opsx_verify, claude_commands_opsx_sync, claude_commands_opsx_archive [INFERRED 0.85]
- **Deletion audit pipeline stages** — openspec_changes_deletion_audit_pipeline_design_d3_ingestion_formats, openspec_changes_deletion_audit_pipeline_design_d4_identity_linking, openspec_changes_deletion_audit_pipeline_design_d5_state_reconstruction, openspec_changes_deletion_audit_pipeline_design_d6_policy_table, openspec_changes_deletion_audit_pipeline_design_d7_step_planning [EXTRACTED 1.00]
- **OpenSpec change artifacts** — openspec_changes_deletion_audit_pipeline_proposal_doc, openspec_changes_deletion_audit_pipeline_design_doc, openspec_changes_deletion_audit_pipeline_specs_deletion_audit_spec_doc, openspec_changes_deletion_audit_pipeline_tasks_doc [EXTRACTED 1.00]
- **OpenSpec skills workflow** — _claude_skills_openspec_propose_skill_doc, _claude_skills_openspec_sync_specs_skill_doc, _claude_skills_openspec_update_change_skill_doc, _claude_skills_openspec_verify_change_skill_doc [INFERRED 0.85]
- **Policy-retained records (audit log, finance register, compliance journal)** — dataset_evidence_documents_legal_retention_register_20260529_retention_policy, dataset_evidence_documents_security_retention_extract_audit_record_003, dataset_evidence_records_customer_account_handover_20261001_security_service [INFERRED 0.75]
- **Northstar Shop internal console screenshots** — dataset_evidence_images_account_admin_console_20260926, dataset_evidence_images_analytics_profile_view_20260713, dataset_evidence_images_backup_restore_console_20260429, dataset_evidence_images_connector_management_console_20260807 [INFERRED 0.85]
- **Northstar Shop admin console evidence screens** — dataset_evidence_images_customer_export_console_20260618, dataset_evidence_images_deleted_account_reference_20260310, dataset_evidence_images_marketing_profile_console, dataset_evidence_images_object_storage_browser_20260213 [INFERRED 0.85]
- **Northstar Shop internal console evidence screenshots** — dataset_evidence_images_search_index_inspector_20260901_screenshot, dataset_evidence_images_security_audit_explorer_20260905_screenshot, dataset_evidence_images_support_ticket_console_20260524_screenshot [INFERRED 0.85]

## Communities (18 total, 3 thin omitted)

### Community 0 - "Trace Submission Rules"
Cohesion: 0.10
Nodes (24): agent-trace.zip submission, Trace location: antigravity, Trace location: claude code, Trace location: codex, Trace location: opencode, Trace location: other harnesses, Constraints that make submission evaluable (deterministic, terminal-runnable), Never use organizer-only truth or golden answers (+16 more)

### Community 1 - "Deletion Decision Rules"
Cohesion: 0.13
Nodes (25): Deletion decision rules, D4 Identity and linking (names never sufficient alone), D5 State reconstruction: latest fact at or before audit_at, replica drift, D6 Policy table from deletion_rules.csv with category resolver and overrides, Policy engine applying deletion_rules.csv, Requirement: account tombstone treatment, Requirement: audit time cutoff, Requirement: claims are not proof (+17 more)

### Community 2 - "Pipeline Architecture"
Cohesion: 0.11
Nodes (22): Evidence rules, D10 Parallelism: 6 workers, sorted collection, D1 Pipeline stages: ingest, index, per-case parallel, sorted write, D2 Fact model: normalized record shape per source, D3 Ingestion per format (SQL, JSON/log, PDF, PNG), D7 Step planning and ordering by operation rank, deterministic serialization, D8 Citation rule: one latest covering file per case, D9 LLM client and SHA-256 keyed cache, temperature 0 (+14 more)

### Community 3 - "OpsX Apply/Explore"
Cohesion: 0.11
Nodes (18): /opsx:apply command (Implement tasks from a change), openspec CLI usage, Project check (openspec list --json root), Store selection (--store flag), /opsx:explore command (Explore mode thinking partner), Explore mode: thinking not implementing, openspec CLI usage, Project check (openspec list --json root) (+10 more)

### Community 4 - "Customer Evidence Documents"
Cohesion: 0.12
Nodes (18): Northstar Shop Customer Statement NST-2026-0718-1842, Order ORD-20261260 and payment record, Delivery Address Correction Request CS-4827, Support ticket CS-4827 attachment (region ap-south), Disputed Orders and Tax Records Register May 2026, Finance Records (register owner), Seven-year retention of disputed order and tax records, Compliance Journal Extract CJX-20260905-0630 (+10 more)

### Community 5 - "Eval Harness and Tasks"
Cohesion: 0.24
Nodes (14): D11 Evaluation harness metrics and weighted headline, Evaluation harness built first, Task group 10: Integration (cold/warm run, code.zip), Task group 1: Setup (requirements, .gitignore, module layout), Task group 2: Evaluation harness first, Task group 3: Dataset loading and identity, Task group 4: LLM client and cache, Task group 5: Evidence ingestion (+6 more)

### Community 6 - "OpsX Archive/Sync"
Cohesion: 0.14
Nodes (14): /opsx:archive command (Archive completed change), openspec CLI usage, Project check (openspec list --json root), Store selection (--store flag), /opsx:sync command (Sync delta specs to main specs), openspec CLI usage, Project check (openspec list --json root), Store selection (--store flag) (+6 more)

### Community 7 - "OpenSpec Propose Workflow"
Cohesion: 0.18
Nodes (13): Change artifacts: proposal, design, specs, tasks, openspec-propose, OpenSpec spec-driven change workflow, Propose change: generate proposal, design, specs, tasks in one step, Delta spec operations: ADDED, MODIFIED, REMOVED, RENAMED, openspec-sync-specs, Sync delta specs (ADDED/MODIFIED/REMOVED/RENAMED) to main specs, openspec-update-change (+5 more)

### Community 8 - "OpsX New/Continue"
Cohesion: 0.17
Nodes (12): /opsx:continue command (Create next artifact), openspec CLI usage, Project check (openspec list --json root), Store selection (--store flag), /opsx:new command (Start new change), openspec CLI usage, Project check (openspec list --json root), Store selection (--store flag) (+4 more)

### Community 9 - "Account Admin Screens"
Cohesion: 0.17
Nodes (12): Account admin console screenshot (2026-09-26), Account record (account service, direct identifiers still present), Customer Operations console (customer profile with email, phone, address, orders, support link), Order records (delivered and returned orders), Linked support ticket and support record, Analytics profile view screenshot (2026-07-13), Analytics profile record exposing email and user reference, Pulse Analytics user profile console (event timeline, sessions, profile attributes) (+4 more)

### Community 10 - "Search Index Screens"
Cohesion: 0.20
Nodes (11): Northstar Shop internal console UI family, customer_directory_v3 search index (prod-eu), Indexed customer document exposing name, email, customer reference, Search Console customer search screenshot (2026-09-01), Near-match email record without reference (decoy), Account closure recorded event (audit_record_003), Sentinel account events screenshot (2026-09-05), Signed account audit events for one user subject (+3 more)

### Community 11 - "Export and Registry Screens"
Cohesion: 0.24
Nodes (10): Customer Download Center data exports screenshot, Export detail: profile, orders, saved addresses; expires after 7 days, Customer data export jobs list (zip packages), Customer Reference Registry retained reference screenshot, Linked records: orders, support cases, finance, Retained customer key reference (account tombstone), Nimbus Object Storage browser screenshot, Support attachment objects (delivery, return labels, invoice) (+2 more)

### Community 12 - "OpsX Update"
Cohesion: 0.50
Nodes (4): /opsx:update command (Revise planning artifacts), openspec CLI usage, Project check (openspec list --json root), Store selection (--store flag)

### Community 13 - "Backup Restore Risk"
Cohesion: 0.50
Nodes (4): Backup restore console screenshot (2026-04-29), Backup archive record (account-keyed archive with retention end and restore history), Restore risk (archive restorable, restores completed), Vault Recovery Manager console (customer-platform weekly archives)

### Community 14 - "Marketing Profile Flow"
Cohesion: 0.67
Nodes (4): Audience Operations marketing profile screenshot, Audience membership, segments and campaign metrics, Profile refreshed from live data (active data flow), Live marketing profile with direct identifiers

## Knowledge Gaps
- **71 isolated node(s):** `openspec CLI usage`, `Store selection (--store flag)`, `Project check (openspec list --json root)`, `openspec CLI usage`, `Store selection (--store flag)` (+66 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 78 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Ghost Data Still Exists challenge` connect `Trace Submission Rules` to `Deletion Decision Rules`, `Eval Harness and Tasks`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Why does `OpenSpec spec-driven change workflow` connect `OpenSpec Propose Workflow` to `Pipeline Architecture`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Why does `Change: deletion-audit-pipeline` connect `Pipeline Architecture` to `Trace Submission Rules`, `Deletion Decision Rules`, `Eval Harness and Tasks`, `OpenSpec Propose Workflow`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Change: deletion-audit-pipeline` (e.g. with `OpenSpec spec-driven change workflow` and `Only allowed model: deepseek/deepseek-v4.1-flash via OpenRouter SDK`) actually correct?**
  _`Change: deletion-audit-pipeline` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `agent-trace.zip submission` (e.g. with `log.txt session logging contract` and `Submission artifacts (code.zip, output.csv, transcript)`) actually correct?**
  _`agent-trace.zip submission` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `D5 State reconstruction: latest fact at or before audit_at, replica drift` (e.g. with `audit_at time cutoff` and `Reported statuses are claims, not proof`) actually correct?**
  _`D5 State reconstruction: latest fact at or before audit_at, replica drift` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `D7 Step planning and ordering by operation rank, deterministic serialization` (e.g. with `Step schema (7 fields)` and `Requirement: deterministic serialization`) actually correct?**
  _`D7 Step planning and ordering by operation rank, deterministic serialization` has 4 INFERRED edges - model-reasoned connections that need verification._