import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))

import loader  # noqa: E402
from identity import IdentityIndex  # noqa: E402


def index():
    return IdentityIndex(loader.load_identities(), loader.load_audit_log())


def test_row_counts():
    assert len(loader.load_requests()) == 518
    assert len(loader.load_samples()) == 32
    assert len(loader.load_rules()) == 15


def test_all_request_emails_resolve_418_current_100_historical():
    idx = index()
    cur = hist = 0
    for r in loader.load_requests():
        s = idx.resolve_email(r.email)
        assert s is not None, r.case_id
        if idx.is_current_email(r.email):
            cur += 1
        else:
            hist += 1
    assert (cur, hist) == (418, 100)


def test_historical_email_pulls_in_current_identifiers():
    idx = index()
    a = next(a for a in loader.load_audit_log() if a.field_name == "email")
    s = idx.resolve_email(a.old_value.upper())
    assert s.user_id == a.user_id
    ident = next(i for i in loader.load_identities() if i.user_id == a.user_id)
    assert ident.email.lower() in s.emails and ident.email_hash in s.hashes
