"""Validate output.csv against the output contract.

Usage: python code/validate_output.py
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import DATASET, OUTPUT  # noqa: E402

ALLOWED = {
    "FINDING": {"REPORT_REMAINING_RECORD": "PRESENT", "REPORT_EXPOSED_PII": "PRESENT",
                "REPORT_ACTIVE_DATA_FLOW": "ACTIVE", "REPORT_RESTORE_RISK": "ACTIVE"},
    "REMEDIATION": {"DISABLE_DATA_FLOW": "DISABLED", "BLOCK_RESTORE": "BLOCKED", "DELETE_RECORD": "ABSENT",
                    "REDACT_RECORD": "REDACTED", "ANONYMIZE_RECORD": "ANONYMIZED"},
    "VERIFICATION": {"VERIFY_RECORD_ABSENT": "ABSENT", "VERIFY_RECORD_PRESENT": "PRESENT",
                     "VERIFY_RECORD_REDACTED": "REDACTED", "VERIFY_RECORD_ANONYMIZED": "ANONYMIZED",
                     "VERIFY_DATA_FLOW_DISABLED": "DISABLED", "VERIFY_RESTORE_BLOCKED": "BLOCKED"},
}
PHASES = ["FINDING", "REMEDIATION", "VERIFICATION"]
FIELDS = {"step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id"}
STATUSES = {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"}


def validate(output_path: Path, requests_path: Path):
    errors = []
    with open(output_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != ["case_id", "deletion_status", "steps_json"]:
            errors.append(f"bad header {reader.fieldnames}")
        rows = list(reader)
    with open(requests_path, newline="", encoding="utf-8") as f:
        want = sorted(r["case_id"] for r in csv.DictReader(f))
    got = [r["case_id"] for r in rows]
    if got != want:
        errors.append(f"case ids differ from requests (rows={len(got)}, expected={len(want)}) or are unsorted")
    for r in rows:
        cid = r["case_id"]
        if r["deletion_status"] not in STATUSES:
            errors.append(f"{cid}: bad status {r['deletion_status']}")
        try:
            steps = json.loads(r["steps_json"])
        except json.JSONDecodeError:
            errors.append(f"{cid}: steps_json is not valid JSON")
            continue
        if r["deletion_status"] == "NOT_APPLICABLE" and steps != []:
            errors.append(f"{cid}: NOT_APPLICABLE must have []")
        last_phase = -1
        for i, s in enumerate(steps, 1):
            if set(s) != FIELDS:
                errors.append(f"{cid}: step {i} fields {sorted(s)}")
                continue
            if s["step_no"] != i:
                errors.append(f"{cid}: step_no {s['step_no']} at position {i}")
            if s["phase"] not in ALLOWED or ALLOWED[s["phase"]].get(s["operation"]) != s["state"]:
                errors.append(f"{cid}: step {i} bad phase/operation/state {s['phase']}/{s['operation']}/{s['state']}")
                continue
            ph = PHASES.index(s["phase"])
            if ph < last_phase:
                errors.append(f"{cid}: step {i} phase out of order")
            last_phase = ph
            cited = bool(s["evidence_id"])
            if s["phase"] == "REMEDIATION" and cited:
                errors.append(f"{cid}: step {i} remediation must have empty evidence_id")
        if r["deletion_status"] == "COMPLETE" and any(s.get("phase") != "VERIFICATION" for s in steps):
            errors.append(f"{cid}: COMPLETE must contain only VERIFICATION steps")
    return errors, len(rows)


def main():
    errors, n = validate(OUTPUT, DATASET / "deletion_requests.csv")
    for e in errors[:50]:
        print("ERROR", e)
    print(f"{n} rows checked, {len(errors)} problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
