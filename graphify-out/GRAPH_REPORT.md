# Graph Report - hackerrank-orchestrate-october26  (2026-10-25)

## Corpus Check
- 53 files · ~92,180 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 385 nodes · 740 edges · 19 communities (17 shown, 2 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 68 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Trace Submission Rules
- loader.py
- ingest.py
- pathlib
- Customer Evidence Documents
- intent.py
- OpsX Archive/Sync
- Evaluation Report
- vision.py
- Account Admin Screens
- Search Index Screens
- Export and Registry Screens
- OpsX Update
- Backup Restore Risk
- Marketing Profile Flow
- OpenSpec Config
- evaluation/main.py
- state.py

## God Nodes (most connected - your core abstractions)
1. `Fact` - 18 edges
2. `Ghost Data Still Exists challenge` - 17 edges
3. `SourceInfo` - 16 edges
4. `extract_refs()` - 12 edges
5. `ingest_file()` - 12 edges
6. `audit()` - 12 edges
7. `assess()` - 12 edges
8. `main()` - 11 edges
9. `IdentityIndex` - 11 edges
10. `system_for_resource()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `Failures found and improvements made` --references--> `ActivityLinker`  [INFERRED]
  evaluation/evaluation_report.md → code/state.py
- `Packaging code.zip` --semantically_similar_to--> `Submission artifacts (code.zip, output.csv, transcript)`  [INFERRED] [semantically similar]
  README.md → problem_statement.md
- `Support ticket CS-4827 attachment (region ap-south)` --semantically_similar_to--> `support_platform (SUPPORT_MESSAGE/ATTACHMENT)`  [INFERRED] [semantically similar]
  dataset/evidence/documents/delivery_correction_attachment.pdf → dataset/evidence/records/customer_account_handover_20261001.txt
- `add()` --indirect_call--> `steps()`  [INFERRED]
  code/planner.py → tests/test_pipeline.py
- `Output format and ordering` --semantically_similar_to--> `Allowed step operations (findings, remediation, verification)`  [INFERRED] [semantically similar]
  README.md → AGENTS.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **LLM prompts used by pipeline** — code_prompts_intent_v1, code_prompts_image_tile_v1, evaluation_usage_cost [INFERRED 0.75]
- **Policy-retained records (audit log, finance register, compliance journal)** — dataset_evidence_documents_legal_retention_register_20260529_retention_policy, dataset_evidence_documents_security_retention_extract_audit_record_003, dataset_evidence_records_customer_account_handover_20261001_security_service [INFERRED 0.75]
- **Northstar Shop admin console evidence screens** — dataset_evidence_images_customer_export_console_20260618, dataset_evidence_images_deleted_account_reference_20260310, dataset_evidence_images_marketing_profile_console, dataset_evidence_images_object_storage_browser_20260213 [INFERRED 0.85]
- **Northstar Shop internal console screenshots** — dataset_evidence_images_account_admin_console_20260926, dataset_evidence_images_analytics_profile_view_20260713, dataset_evidence_images_backup_restore_console_20260429, dataset_evidence_images_connector_management_console_20260807 [INFERRED 0.85]
- **Northstar Shop internal console evidence screenshots** — dataset_evidence_images_search_index_inspector_20260901_screenshot, dataset_evidence_images_security_audit_explorer_20260905_screenshot, dataset_evidence_images_support_ticket_console_20260524_screenshot [INFERRED 0.85]
- **Required submission deliverables** — problem_statement_submission_artifacts, evaluation_evaluation_report, evaluation_usage_report, readme_packaging [INFERRED 0.85]

## Communities (19 total, 2 thin omitted)

### Community 0 - "Trace Submission Rules"
Cohesion: 0.06
Nodes (48): classify(), classify_all(), parse_decision(), prior_classifications(), Request-intent gate: one cached LLM call per case decides if deletion is…, CLASSIFY_REQUEST events at or before audit_at for the given resources., Run classification in a 6-worker pool; results are keyed by case_id so order…, LLMClient (+40 more)

### Community 1 - "loader.py"
Cohesion: 0.07
Nodes (35): base64, OpenRouter client for the single allowed model, with a disk cache and usage…, files(), main(), Build code.zip (runnable solution, prompts, config, README, evaluation reports)…, Repo-root-relative paths shared by all modules., Stderr progress for long stages: a live bar on a terminal, 10% line steps…, main() (+27 more)

### Community 2 - "ingest.py"
Cohesion: 0.10
Nodes (28): IdentityIndex, norm_email(), norm_phone(), norm_value(), Identity resolution over current and historical identifiers. Rules: emails and…, All normalized identifier strings (user_id, emails, phones, hashes)., user_id owning a normalized identifier (email, phone digits, hash, user_id)., Subject (+20 more)

### Community 3 - "pathlib"
Cohesion: 0.14
Nodes (34): _bool(), derive_state(), extract_refs(), Fact, ingest_all(), ingest_file(), ingest_free_text(), ingest_image() (+26 more)

### Community 4 - "Customer Evidence Documents"
Cohesion: 0.07
Nodes (34): agent-trace.zip submission, Trace location: antigravity, Trace location: claude code, Trace location: codex, Trace location: opencode, Trace location: other harnesses, AGENTS.md agent rules, Deletion decision rules (+26 more)

### Community 5 - "intent.py"
Cohesion: 0.17
Nodes (21): argparse, citation_validity(), custom_results(), determinism(), headline(), history_rows(), known_ids(), main() (+13 more)

### Community 6 - "OpsX Archive/Sync"
Cohesion: 0.16
Nodes (16): fixture, main, parametrize, expected(), _index(), key(), sample_rows(), steps() (+8 more)

### Community 7 - "Evaluation Report"
Cohesion: 0.12
Nodes (18): Northstar Shop Customer Statement NST-2026-0718-1842, Order ORD-20261260 and payment record, Delivery Address Correction Request CS-4827, Support ticket CS-4827 attachment (region ap-south), Disputed Orders and Tax Records Register May 2026, Finance Records (register owner), Seven-year retention of disputed order and tax records, Compliance Journal Extract CJX-20260905-0630 (+10 more)

### Community 8 - "vision.py"
Cohesion: 0.17
Nodes (14): Versioned prompts: prompts/<name>/<version>.txt, with the active version of…, content_bottom(), has_text(), _png(), Path, Screenshot reading: crop the table and detail panel into tiles, transcribe each…, First y at or after y0 where MAX_GAP consecutive blank rows follow the last…, False for tiles that hold only background, row stripes and borders (the model… (+6 more)

### Community 9 - "Account Admin Screens"
Cohesion: 0.17
Nodes (16): Account tombstone (retain stable user ref, redact identifiers), Allowed step operations and states, audit_at time cutoff, Reported statuses are claims, not proof, Deletion-audit agent, deletion_rules.csv policy, deletion_status: COMPLETE/INCOMPLETE/NOT_APPLICABLE, evaluation_report.md and usage_report.md (+8 more)

### Community 10 - "Search Index Screens"
Cohesion: 0.17
Nodes (12): Account admin console screenshot (2026-09-26), Account record (account service, direct identifiers still present), Customer Operations console (customer profile with email, phone, address, orders, support link), Order records (delivered and returned orders), Linked support ticket and support record, Analytics profile view screenshot (2026-07-13), Analytics profile record exposing email and user reference, Pulse Analytics user profile console (event timeline, sessions, profile attributes) (+4 more)

### Community 11 - "Export and Registry Screens"
Cohesion: 0.20
Nodes (8): cache_key(), LLMError, _openrouter_transport(), Path, Real call through the OpenRouter SDK. Returns (content, input_tokens,…, Return the model response, from cache when the same model/prompt/input was seen., RuntimeError, Transport

### Community 12 - "OpsX Update"
Cohesion: 0.20
Nodes (11): Northstar Shop internal console UI family, customer_directory_v3 search index (prod-eu), Indexed customer document exposing name, email, customer reference, Search Console customer search screenshot (2026-09-01), Near-match email record without reference (decoy), Account closure recorded event (audit_record_003), Sentinel account events screenshot (2026-09-05), Signed account audit events for one user subject (+3 more)

### Community 13 - "Backup Restore Risk"
Cohesion: 0.24
Nodes (10): Customer Download Center data exports screenshot, Export detail: profile, orders, saved addresses; expires after 7 days, Customer data export jobs list (zip packages), Customer Reference Registry retained reference screenshot, Linked records: orders, support cases, finance, Retained customer key reference (account tombstone), Nimbus Object Storage browser screenshot, Support attachment objects (delivery, return labels, invoice) (+2 more)

### Community 14 - "Marketing Profile Flow"
Cohesion: 0.42
Nodes (9): importlib_util, pytest_approx(), row(), step(), test_determinism(), test_future_dated_citation_is_flagged(), test_headline_formula(), test_perfect_match_scores_100() (+1 more)

### Community 16 - "evaluation/main.py"
Cohesion: 0.50
Nodes (4): Backup restore console screenshot (2026-04-29), Backup archive record (account-keyed archive with retention end and restore history), Restore risk (archive restorable, restores completed), Vault Recovery Manager console (customer-platform weekly archives)

### Community 17 - "state.py"
Cohesion: 0.67
Nodes (4): Audience Operations marketing profile screenshot, Audience membership, segments and campaign metrics, Profile refreshed from live data (active data flow), Live marketing profile with direct identifiers

## Knowledge Gaps
- **35 isolated node(s):** `Usage Report`, `Citation problems`, `Custom cases (participant-authored, reported separately)`, `Determinism differences`, `Metrics (32 public samples and custom cases; never the 518 evaluation requests)` (+30 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 115 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Evaluation Report` connect `Customer Evidence Documents` to `Trace Submission Rules`?**
  _High betweenness centrality (0.196) - this node is a cross-community bridge._
- **Why does `Failures found and improvements made` connect `Trace Submission Rules` to `Customer Evidence Documents`?**
  _High betweenness centrality (0.195) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `Fact` (e.g. with `Policy` and `FactIndex`) actually correct?**
  _`Fact` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `SourceInfo` (e.g. with `FactIndex` and `_index()`) actually correct?**
  _`SourceInfo` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Usage Report`, `Citation problems`, `Custom cases (participant-authored, reported separately)` to the rest of the system?**
  _35 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Trace Submission Rules` be split into smaller, more focused modules?**
  _Cohesion score 0.06398809523809523 - nodes in this community are weakly interconnected._
- **Should `loader.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06567992599444958 - nodes in this community are weakly interconnected._