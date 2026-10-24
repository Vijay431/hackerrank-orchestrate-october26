"""Status decision and step generation."""
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from ingest import EMAIL_RE, HASH_RE
from policy import Policy
from state import (ABSENT_STATES, PRESENT_STATES, FactIndex, Linked, Observation, observe)

FINDING_RANK = {"REPORT_REMAINING_RECORD": 0, "REPORT_EXPOSED_PII": 1, "REPORT_ACTIVE_DATA_FLOW": 2,
                "REPORT_RESTORE_RISK": 3}
REMEDIATION_RANK = {"DISABLE_DATA_FLOW": 0, "BLOCK_RESTORE": 1, "DELETE_RECORD": 2, "REDACT_RECORD": 3,
                    "ANONYMIZE_RECORD": 4}
VERIFICATION_RANK = {"VERIFY_RECORD_ABSENT": 0, "VERIFY_RECORD_PRESENT": 1, "VERIFY_RECORD_REDACTED": 2,
                     "VERIFY_RECORD_ANONYMIZED": 3, "VERIFY_DATA_FLOW_DISABLED": 4, "VERIFY_RESTORE_BLOCKED": 5}
FINDING_STATE = {"REPORT_REMAINING_RECORD": "PRESENT", "REPORT_EXPOSED_PII": "PRESENT",
                 "REPORT_ACTIVE_DATA_FLOW": "ACTIVE", "REPORT_RESTORE_RISK": "ACTIVE"}
REMEDIATION_STATE = {"DISABLE_DATA_FLOW": "DISABLED", "BLOCK_RESTORE": "BLOCKED", "DELETE_RECORD": "ABSENT",
                     "REDACT_RECORD": "REDACTED", "ANONYMIZE_RECORD": "ANONYMIZED"}
VERIFICATION_STATE = {"VERIFY_RECORD_ABSENT": "ABSENT", "VERIFY_RECORD_PRESENT": "PRESENT",
                      "VERIFY_RECORD_REDACTED": "REDACTED", "VERIFY_RECORD_ANONYMIZED": "ANONYMIZED",
                      "VERIFY_DATA_FLOW_DISABLED": "DISABLED", "VERIFY_RESTORE_BLOCKED": "BLOCKED"}
ACTION_TO_FIX = {"DELETE": ("REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT"),
                 "REDACT": ("REPORT_EXPOSED_PII", "REDACT_RECORD", "VERIFY_RECORD_REDACTED"),
                 "ANONYMIZE": ("REPORT_EXPOSED_PII", "ANONYMIZE_RECORD", "VERIFY_RECORD_ANONYMIZED"),
                 "DISABLE": ("REPORT_ACTIVE_DATA_FLOW", "DISABLE_DATA_FLOW", "VERIFY_DATA_FLOW_DISABLED"),
                 "BLOCK": ("REPORT_RESTORE_RISK", "BLOCK_RESTORE", "VERIFY_RESTORE_BLOCKED")}


@dataclass
class Item:
    system_id: str
    resource_id: str
    evidence_id: str
    finding: Optional[str]     # operation or None when already compliant
    remediation: Optional[str]
    verification: str


def _parse_date(s: str) -> Optional[str]:
    """Normalize '2031-12-31T23:59:59Z' or '25 Aug 2027' to an ISO date string."""
    if not s:
        return None
    if re.match(r"\d{4}-\d{2}-\d{2}", s):
        return s[:10]
    try:
        return datetime.strptime(s, "%d %b %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def _exposed(fact, identity_values, direct_only: bool) -> bool:
    if fact is None:
        return False
    for r in fact.refs:
        if r in identity_values:
            if direct_only and r.startswith("user_"):
                continue
            return True
    return False


def _flag(attrs: dict, key: str):
    v = attrs.get(key)
    if v is None:
        return None
    return str(v).lower() in ("1", "true", "yes")


def assess(link: Linked, req_audit_at: str, identity_values, index: FactIndex, policy: Policy) -> Optional[Item]:
    facts = [f for f in index.by_resource.get(link.resource_id, ())
             if f.observed_at <= req_audit_at and f.captured_at <= req_audit_at] or \
            [f for f in index.by_resource.get(link.resource_id, ()) if f.observed_at <= req_audit_at]
    category = policy.category(link.resource_id, facts)
    treat = policy.treatment(category)
    obs = observe(link.resource_id, link.system_id, req_audit_at, index)
    ev = obs.source_id if obs and obs.source_id else (link.activity_ids[0] if link.activity_ids else "")
    f = obs.fact if obs else None
    action = treat.action
    present = obs is not None and obs.state in PRESENT_STATES

    if action == "RETAIN":
        if category == "SECURITY_AUDIT_LOG":
            until = None
            for x in facts:
                until = _parse_date(str(x.attrs.get("retention_until") or x.attrs.get("retain_until") or "")) or until
            if until and until <= req_audit_at[:10]:
                action = "DELETE"
        if action == "RETAIN":
            return Item(link.system_id, link.resource_id, ev, None, None, "VERIFY_RECORD_PRESENT")

    if action == "DELETE":
        if present:
            return Item(link.system_id, link.resource_id, ev, *ACTION_TO_FIX["DELETE"][:2], "VERIFY_RECORD_ABSENT")
        return Item(link.system_id, link.resource_id, ev, None, None, "VERIFY_RECORD_ABSENT")

    if action in ("REDACT", "ANONYMIZE"):
        exposed = (obs is not None and obs.state == "IDENTIFIABLE") or \
                  (present and _exposed(f, identity_values, direct_only=(action == "REDACT")))
        fix = ACTION_TO_FIX[action]
        return Item(link.system_id, link.resource_id, ev, fix[0] if exposed else None,
                    fix[1] if exposed else None, fix[2])

    if action == "DISABLE":
        active = obs is not None and obs.state == "ACTIVE"
        return Item(link.system_id, link.resource_id, ev, "REPORT_ACTIVE_DATA_FLOW" if active else None,
                    "DISABLE_DATA_FLOW" if active else None, "VERIFY_DATA_FLOW_DISABLED")

    if action == "BLOCK":
        allowed = None
        if f is not None:
            allowed = _flag(f.attrs, "restore_allowed")
            if allowed is None and _flag(f.attrs, "eligible") is not None:
                allowed = _flag(f.attrs, "eligible") and not _flag(f.attrs, "deletion_block")
        if allowed is None:  # no explicit restore flag: an archive that is found and not blocked can be restored
            allowed = obs is not None and obs.state in PRESENT_STATES
        risky = bool(allowed)
        return Item(link.system_id, link.resource_id, ev, "REPORT_RESTORE_RISK" if risky else None,
                    "BLOCK_RESTORE" if risky else None, "VERIFY_RESTORE_BLOCKED")
    return None


def build_steps(items: List[Item]):
    """Return (status, steps) for the assessed items."""
    findings = sorted((i for i in items if i.finding),
                      key=lambda i: (FINDING_RANK[i.finding], i.system_id, i.resource_id))
    remed = sorted((i for i in items if i.remediation),
                   key=lambda i: (REMEDIATION_RANK[i.remediation], i.system_id, i.resource_id))
    verif = sorted(items, key=lambda i: (VERIFICATION_RANK[i.verification], i.system_id, i.resource_id))
    steps = []

    def add(phase, i, op, state, ev):
        steps.append({"step_no": len(steps) + 1, "phase": phase, "system_id": i.system_id,
                      "resource_id": i.resource_id, "operation": op, "state": state, "evidence_id": ev})

    if not findings:  # COMPLETE
        for i in verif:
            add("VERIFICATION", i, i.verification, VERIFICATION_STATE[i.verification], i.evidence_id)
        return "COMPLETE", steps
    for i in findings:
        add("FINDING", i, i.finding, FINDING_STATE[i.finding], i.evidence_id)
    for i in remed:
        add("REMEDIATION", i, i.remediation, REMEDIATION_STATE[i.remediation], "")
    for i in verif:
        add("VERIFICATION", i, i.verification, VERIFICATION_STATE[i.verification], "")
    return "INCOMPLETE", steps


def serialize(steps) -> str:
    return json.dumps(steps, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
