"""Data-category resolution and policy treatment from deletion_rules.csv."""
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from ingest import Fact, RESOURCE_RE
from loader import Rule

PREFIX_CATEGORY = {
    "account": "USER_PROFILE", "search": "SEARCH_INDEX_ENTRY", "analytics": "ANALYTICS_PROFILE",
    "support": "SUPPORT_MESSAGE", "export": "USER_EXPORT", "data_flow": "DATA_FLOW",
    "backup": "BACKUP_ARCHIVE", "audit_record": "SECURITY_AUDIT_LOG", "tombstone": "ACCOUNT_TOMBSTONE",
    "legal_hold": "LEGAL_HOLD_RECORD", "cache": "CACHE_ENTRY", "email_delivery": "EMAIL_DELIVERY_LOG",
}
# Categories not in deletion_rules.csv but required for flow findings.
FLOW_CATEGORY = "DATA_FLOW"

ACTION_STATE = {"DELETE": "ABSENT", "REDACT": "REDACTED", "ANONYMIZE": "ANONYMIZED", "RETAIN": "PRESENT"}


@dataclass
class Treatment:
    category: str
    action: str            # DELETE / REDACT / ANONYMIZE / RETAIN / DISABLE (data flow) / BLOCK (backup)
    unresolved: bool = False


class Policy:
    def __init__(self, rules: Iterable[Rule]):
        self.rules: Dict[str, Rule] = {r.data_category: r for r in rules}
        self.unresolved = 0

    def category(self, rid: str, facts: List[Fact]) -> str:
        """Category from evidence content first, then the resource id prefix."""
        for f in facts:
            if f.category in self.rules or f.category == FLOW_CATEGORY:
                cat = f.category
                if cat == "SUPPORT_MESSAGE" and "file" in f.attrs:
                    return "SUPPORT_ATTACHMENT"
                if cat:
                    return cat
        for f in facts:
            if f.attrs.get("service") == "support_replica" or "legacy_contact_index" in str(f.attrs.get("source", "")):
                return "SECONDARY_IDENTIFIER"
        for f in facts:
            ev = str(f.attrs.get("event", ""))
            if ev.startswith("attachment_") or "file" in f.attrs and str(rid).startswith("support"):
                return "SUPPORT_ATTACHMENT"
            if ev == "contact_lookup_completed" or "email_opt_in" in f.attrs:
                return "MARKETING_PROFILE"
            if "audience_cohort" in f.attrs and str(rid).startswith("analytics"):
                return "ANALYTICS_PROFILE"
        m = RESOURCE_RE.fullmatch(rid)
        if m:
            return PREFIX_CATEGORY[m.group(1)]
        self.unresolved += 1
        return "UNRESOLVED"

    def treatment(self, category: str) -> Treatment:
        if category == FLOW_CATEGORY:
            return Treatment(category, "DISABLE")
        if category == "BACKUP_ARCHIVE":
            return Treatment(category, "BLOCK")
        rule = self.rules.get(category)
        if not rule:
            return Treatment(category, "NONE", unresolved=True)
        return Treatment(category, rule.required_action)
