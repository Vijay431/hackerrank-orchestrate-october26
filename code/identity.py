"""Identity resolution over current and historical identifiers.

Rules: emails and hashes compare case-insensitively, phones compare on digits
only. Names are never used as an identifier on their own.
"""
import re
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, List, Optional

from loader import AuditEntry, Identity


def norm_email(v: str) -> str:
    return v.strip().lower()


def norm_phone(v: str) -> str:
    return re.sub(r"\D", "", v)


def norm_value(field_name: str, v: str) -> str:
    return norm_phone(v) if field_name == "phone" else v.strip().lower()


@dataclass
class Subject:
    user_id: str
    name: str
    emails: FrozenSet[str] = field(default_factory=frozenset)
    phones: FrozenSet[str] = field(default_factory=frozenset)
    hashes: FrozenSet[str] = field(default_factory=frozenset)

    def values(self) -> FrozenSet[str]:
        """All normalized identifier strings (user_id, emails, phones, hashes)."""
        return frozenset({self.user_id.lower(), *self.emails, *self.phones, *self.hashes})


class IdentityIndex:
    def __init__(self, identities: Iterable[Identity], audit: Iterable[AuditEntry]):
        identities = list(identities)
        emails: Dict[str, set] = {}
        phones: Dict[str, set] = {}
        hashes: Dict[str, set] = {}
        names: Dict[str, str] = {}
        for i in identities:
            names[i.user_id] = i.name
            emails.setdefault(i.user_id, set()).add(norm_email(i.email))
            if norm_phone(i.phone):
                phones.setdefault(i.user_id, set()).add(norm_phone(i.phone))
            hashes.setdefault(i.user_id, set()).add(i.email_hash.strip().lower())
        for a in audit:
            target = {"email": emails, "phone": phones, "email_hash": hashes}.get(a.field_name)
            if target is None:
                continue
            for v in (a.old_value, a.new_value):
                n = norm_value("phone" if a.field_name == "phone" else a.field_name, v)
                if n:
                    target.setdefault(a.user_id, set()).add(n)
        self._subjects: Dict[str, Subject] = {}
        for uid in sorted(set(emails) | set(names)):
            self._subjects[uid] = Subject(
                uid, names.get(uid, ""), frozenset(emails.get(uid, ())),
                frozenset(phones.get(uid, ())), frozenset(hashes.get(uid, ())),
            )
        self._by_email: Dict[str, str] = {}
        for uid, s in self._subjects.items():
            for e in s.emails:
                self._by_email.setdefault(e, uid)
        self._current = {norm_email(i.email) for i in identities}

    def resolve_email(self, email: str) -> Optional[Subject]:
        uid = self._by_email.get(norm_email(email))
        return self._subjects.get(uid) if uid else None

    def subject(self, user_id: str) -> Optional[Subject]:
        return self._subjects.get(user_id)

    def is_current_email(self, email: str) -> bool:
        return norm_email(email) in self._current
