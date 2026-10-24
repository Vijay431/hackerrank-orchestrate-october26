"""Evidence ingestion: every evidence file becomes normalized Facts.

A Fact is one observation of one resource at one time. Evidence is connected to
a case later, through identifiers in Fact.refs, never through the manifest.
"""
import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from identity import norm_phone
from loader import EvidenceFile
from paths import CACHE, DATASET, EVIDENCE, PROMPTS

RESOURCE_PREFIX_SYSTEM = {
    "account": "account_service", "search": "search_service", "analytics": "analytics_platform",
    "support": "support_platform", "export": "export_service", "data_flow": "integration_service",
    "backup": "backup_service", "audit_record": "security_service", "tombstone": "identity_service",
    "legal_hold": "legal_service", "cache": "cache_service", "email_delivery": "email_delivery_service",
}
RESOURCE_RE = re.compile(r"\b(" + "|".join(sorted(RESOURCE_PREFIX_SYSTEM, key=len, reverse=True)) + r")_(\d+)\b")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
USER_RE = re.compile(r"\buser_\d+\b")
HASH_RE = re.compile(r"\b[0-9a-f]{64}\b")
REGISTER_RE = re.compile(r"(ORD-\d+)\s*\|\s*(user_\d+)\s*\|[^\n]*?Retain until\s+(\d{1,2} \w{3} \d{4})")
STATEMENT_RE = re.compile(r"\bNST-\d{4}-\d{4}-\d{4}\b")
ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
PHONE_KEYS = ("phone",)

SQL_TABLES = {  # table -> (system_id, category hint)
    "customer_profiles": ("account_service", "USER_PROFILE"),
    "customer_profiles_primary": ("account_service", "USER_PROFILE"),
    "customer_profiles_failover_replica": ("account_service", "USER_PROFILE"),
    "customer_search_documents": ("search_service", "SEARCH_INDEX_ENTRY"),
    "search_documents_primary": ("search_service", "SEARCH_INDEX_ENTRY"),
    "customer_analytics_profiles": ("analytics_platform", "ANALYTICS_PROFILE"),
    "support_records": ("support_platform", "SUPPORT_MESSAGE"),
    "customer_exports": ("export_service", "USER_EXPORT"),
    "connector_subscriptions": ("integration_service", "DATA_FLOW"),
    "backup_restore_entries": ("backup_service", "BACKUP_ARCHIVE"),
    "security_audit_records": ("security_service", "SECURITY_AUDIT_LOG"),
}
COLLECTION_CATEGORY = {
    "customer_profiles": "USER_PROFILE", "customer_search_documents": "SEARCH_INDEX_ENTRY",
    "customer_analytics_reports": "ANALYTICS_PROFILE", "customer_analytics_profiles": "ANALYTICS_PROFILE",
    "support_conversations": "SUPPORT_MESSAGE", "ticket_attachments": "SUPPORT_ATTACHMENT",
    "customer_export_jobs": "USER_EXPORT", "connector_configurations": "DATA_FLOW",
    "backup_catalog": "BACKUP_ARCHIVE", "security_audit_events": "SECURITY_AUDIT_LOG",
    "retained_order_records": "LEGAL_HOLD_RECORD", "deleted_customer_references": "ACCOUNT_TOMBSTONE",
}
RECORD_TYPE_CATEGORY = {"DATA_FLOW": "DATA_FLOW"}


@dataclass
class Fact:
    source_id: str
    captured_at: str            # manifest capture time of the file
    observed_at: str            # time the observation describes
    system_id: str
    resource_id: Optional[str]
    category: Optional[str] = None
    state: Optional[str] = None  # normalized: FOUND / NOT_FOUND / ACTIVE / DISABLED / ... or None
    store: str = "primary"      # primary or a replica kind
    refs: frozenset = frozenset()
    attrs: Dict[str, object] = field(default_factory=dict)


@dataclass
class Snap:
    """A point-in-time dump of one system: resources it lacks were absent at `time`."""
    system_id: str
    time: str
    resources: frozenset


@dataclass
class SourceInfo:
    file_id: str
    captured_at: str
    path: str
    kind: str
    facts: List[Fact] = field(default_factory=list)
    coverage: Dict[str, str] = field(default_factory=dict)  # system_id -> time the snapshot covers
    snaps: List[Snap] = field(default_factory=list)
    skipped: Optional[str] = None

    @property
    def store(self) -> str:
        """Capture family (file name without its date), used to compare snapshots of the same store."""
        stem = Path(self.path).stem
        return re.sub(r"_?\d{8}(_\d{6})?$", "", stem)


def system_for_resource(rid: Optional[str]) -> Optional[str]:
    m = RESOURCE_RE.fullmatch(rid or "")
    return RESOURCE_PREFIX_SYSTEM[m.group(1)] if m else None


def _walk(obj, key=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk(v, k)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v, key)
    elif obj is not None:
        yield key, obj


def extract_refs(obj) -> frozenset:
    """Normalized identifier strings (emails, user ids, hashes, phone digits) found anywhere in obj."""
    out = set()
    for key, v in _walk(obj):
        s = str(v)
        out.update(e.lower() for e in EMAIL_RE.findall(s))
        out.update(u.lower() for u in USER_RE.findall(s))
        out.update(HASH_RE.findall(s.lower()))
        if any(p in key for p in PHONE_KEYS):
            d = norm_phone(s)
            if len(d) >= 7:
                out.add(d)
    return frozenset(out)


def _bool(v):
    if isinstance(v, bool):
        return v
    return str(v).lower() in ("1", "true", "yes")


def derive_state(attrs: dict) -> Optional[str]:
    """Normalize the observation outcome from whichever fields a source provides."""
    for k in ("result", "state", "status"):
        v = attrs.get(k)
        if isinstance(v, str) and v.upper() in {"FOUND", "NOT_FOUND", "IDENTIFIABLE", "REDACTED", "ANONYMIZED", "ACTIVE", "DISABLED", "BLOCKED", "PRESENT", "ABSENT"}:
            return v.upper()
    if attrs.get("detector"):
        return "IDENTIFIABLE"
    hs = attrs.get("http_status", attrs.get("status_code"))
    if hs is not None and str(hs).isdigit():
        return "NOT_FOUND" if int(hs) == 404 else ("FOUND" if int(hs) == 200 else None)
    if attrs.get("result") in ("hit", "miss"):
        return "FOUND" if attrs["result"] == "hit" else "NOT_FOUND"
    if "rows" in attrs and str(attrs["rows"]).isdigit():
        return "FOUND" if int(attrs["rows"]) > 0 else "NOT_FOUND"
    if "enabled" in attrs and attrs["enabled"] is not None:
        return "ACTIVE" if _bool(attrs["enabled"]) else "DISABLED"
    return None


# ---------------------------------------------------------------- SQL

def _sql_header(text: str) -> Tuple[Optional[str], str]:
    cap = re.search(r"--\s*Captured at:\s*(\S+)", text)
    topo = re.search(r"--\s*Database topology:\s*(\S+)", text)
    return (cap.group(1) if cap else None), (topo.group(1) if topo else "primary_only")


def ingest_sql(info: SourceInfo, text: str):
    header_cap, topology = _sql_header(text)
    db = sqlite3.connect(":memory:")
    db.executescript(text)
    db.row_factory = sqlite3.Row
    tables = [r[0] for r in db.execute("select name from sqlite_master where type='table' order by name")]
    scope: Dict[str, str] = {}
    if "snapshot_scope" in tables:
        scope = {r["origin_system"]: r["captured_at"] for r in db.execute("select * from snapshot_scope")}
    info.coverage.update(scope)
    for t in tables:
        if t == "snapshot_scope":
            continue
        store = "primary" if t.endswith("primary") or t in SQL_TABLES else t.replace("customer_data_", "")
        for row in db.execute(f'select * from "{t}"'):
            d = dict(row)
            if "record_json" in d:
                rec = json.loads(d["record_json"])
                system = d["origin_system"]
                cat = COLLECTION_CATEGORY.get(d["collection_name"])
                attrs = {**rec, "collection_name": d["collection_name"], "updated_at": d.get("updated_at")}
            else:
                system, cat = SQL_TABLES.get(t, (system_for_resource(d.get("resource_id")), None))
                attrs = d
            observed = scope.get(system) or header_cap or info.captured_at
            if system and system not in info.coverage:
                info.coverage[system] = observed
            attrs = dict(attrs)
            if "enabled" in attrs:
                attrs["enabled"] = bool(attrs["enabled"])
            if "restore_allowed" in attrs:
                attrs["restore_allowed"] = bool(attrs["restore_allowed"])
            info.facts.append(Fact(info.file_id, info.captured_at, observed, system, d["resource_id"], cat,
                                   derive_state(attrs) or "FOUND", store, extract_refs(attrs), attrs))
    if topology != "primary_only" or not scope:
        for s in {f.system_id for f in info.facts if f.system_id}:
            info.coverage.setdefault(s, header_cap or info.captured_at)
    for system, when in info.coverage.items():
        rids = frozenset(f.resource_id for f in info.facts if f.system_id == system and f.resource_id)
        info.snaps.append(Snap(system, when, rids))


# ---------------------------------------------------------------- JSON

def _lookup_fact(info, rec, observed, system=None):
    attrs = dict(rec)
    rid = rec.get("resource_id")
    sysid = system or rec.get("system") or system_for_resource(rid)
    cat = rec.get("record_type")
    return Fact(info.file_id, info.captured_at, observed, sysid, rid, cat, derive_state(attrs), "primary",
                extract_refs(rec), attrs)


def ingest_json(info: SourceInfo, text: str):
    d = json.loads(text)
    if "snapshots" in d:
        for snap in d["snapshots"]:
            sysid, coll, cap = snap["data_store"], snap["collection"], snap["captured_at"]
            info.coverage[sysid] = max(info.coverage.get(sysid, ""), cap)
            if not snap.get("records"):  # an empty extract states that the store held nothing
                info.snaps.append(Snap(sysid, cap, frozenset()))
            for rec in snap.get("records", []):
                attrs = dict(rec)
                attrs["collection_name"] = coll
                info.facts.append(Fact(info.file_id, info.captured_at, cap, sysid, rec.get("resource_id"),
                                       COLLECTION_CATEGORY.get(coll), derive_state(attrs) or "FOUND", "primary",
                                       extract_refs(rec), attrs))
    elif "service_exports" in d:
        for sysid, groups in d["service_exports"].items():
            for gname, items in groups.items():
                for rec in items:
                    obs = rec.get("observed_at", d["exported_at"])
                    info.coverage[sysid] = max(info.coverage.get(sysid, ""), obs)
                    attrs = dict(rec)
                    attrs["group"] = gname
                    info.facts.append(Fact(info.file_id, info.captured_at, obs, sysid, rec.get("resource_id"),
                                           None, derive_state(attrs) or "FOUND", "primary", extract_refs(rec), attrs))
    else:
        recs = d.get("records", [])
        stamp = d.get("captured_at") or d.get("exported_at") or info.captured_at
        for rec in recs:
            if "record_type" in rec and "system" in rec:
                obs = rec.get("recorded_at", stamp)
                f = _lookup_fact(info, rec, obs)
            else:
                obs = stamp
                coll = d.get("collection")
                sysid = system_for_resource(rec.get("resource_id"))
                f = Fact(info.file_id, info.captured_at, obs, sysid, rec.get("resource_id"),
                         COLLECTION_CATEGORY.get(coll), derive_state(rec) or "FOUND", "primary",
                         extract_refs(rec), dict(rec))
            if f.system_id:
                info.coverage[f.system_id] = max(info.coverage.get(f.system_id, ""), f.observed_at)
            info.facts.append(f)


# ---------------------------------------------------------------- logs

KV_RE = re.compile(r'([A-Za-z_][\w.]*)=("(?:[^"\\]|\\.)*"|\S*)')
TRACE_KEYS = ("lookup_key", "correlation_key", "match_key", "scan_key", "subject_ref", "query_key")


def _unq(v: str) -> str:
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        v = v[1:-1].replace('\\"', '"')
    return v


def parse_log_line(line: str) -> Optional[dict]:
    m = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s+(.*)", line.strip())
    if not m:
        return None
    ts, rest = m.groups()
    rec: dict = {"_ts": ts}
    if rest.startswith("{"):
        rec.update({k: v for k, v in json.loads(rest).items()})
        return rec
    mm = re.search(r'message="((?:[^"\\]|\\.)*)"', rest)
    if mm:  # cloud runtime export
        head = rest[:mm.start()]
        rec.update({k: _unq(v) for k, v in KV_RE.findall(head)})
        rest = mm.group(1).replace('\\"', '"')
        rec["service"] = rec.get("function", rec.get("service"))
        rec.update({k: _unq(v) for k, v in KV_RE.findall(rest)})
        return rec
    sysl = re.match(r"<\d+>1 \S+ (\S+) (\S+) - - (.*)", rest)
    if sysl:  # syslog
        rec["service"], rec["trace_id"] = sysl.group(1), sysl.group(2)
        rest = sysl.group(3)
    rec.update({k: _unq(v) for k, v in KV_RE.findall(rest)})
    return rec


def ingest_log(info: SourceInfo, text: str):
    recs = []
    for line in text.splitlines():
        try:
            r = parse_log_line(line)
        except json.JSONDecodeError:
            r = None
        if r:
            recs.append(r)
    refs_by_trace: Dict[str, set] = {}
    for r in recs:
        tid = r.get("trace_id")
        if tid:
            refs_by_trace.setdefault(tid, set()).update(extract_refs({k: v for k, v in r.items() if v != "null"}))
    for r in recs:
        rid = r.get("resource_id")
        if not rid or rid == "null":
            continue
        ev = r.get("event", "")
        if ev.endswith("_started"):
            continue
        attrs = {k: (None if v == "null" else v) for k, v in r.items()}
        refs = set(extract_refs(attrs))
        refs |= refs_by_trace.get(r.get("trace_id"), set())
        system = attrs.get("system") or attrs.get("service")
        if system not in RESOURCE_PREFIX_SYSTEM.values():
            system = system_for_resource(rid) or system
        info.coverage[system] = max(info.coverage.get(system, ""), r["_ts"])
        info.facts.append(Fact(info.file_id, info.captured_at, r["_ts"], system, rid, attrs.get("record_type"),
                               derive_state(attrs) or "FOUND", "primary", frozenset(refs), attrs))


# ---------------------------------------------------------------- text / PDF

HANDOVER_RE = re.compile(r"^-\s*(\S+)\s*\|\s*(\w+)\s*\|\s*(\S+)\s*\|\s*(\w+)\s*\|\s*(\w+)\s*\|\s*(.*?)\s*$")


def ingest_text(info: SourceInfo, text: str):
    for line in text.splitlines():
        m = HANDOVER_RE.match(line)
        if m:
            ts, sysid, rid, cat, state, ref = m.groups()
            attrs = {"subject_reference": ref, "result": state, "record_type": cat}
            info.coverage[sysid] = max(info.coverage.get(sysid, ""), ts)
            info.facts.append(Fact(info.file_id, info.captured_at, ts, sysid, rid, cat, state, "primary",
                                   extract_refs(attrs), attrs))
        else:
            ingest_free_text(info, line)


def ingest_free_text(info: SourceInfo, text: str, observed: Optional[str] = None):
    """Regex fallback: one Fact per resource id, refs from the surrounding text."""
    doc_refs = extract_refs({"t": text})
    for m in RESOURCE_RE.finditer(text):
        rid = m.group(0)
        info.facts.append(Fact(info.file_id, info.captured_at, observed or info.captured_at,
                               system_for_resource(rid), rid, None, None, "primary", doc_refs, {"text": True}))


def pdf_text(file_id: str, path: Path) -> str:
    cached = CACHE / "evidence" / f"{file_id}.txt"
    if cached.exists():
        return cached.read_text(encoding="utf-8")
    from pypdf import PdfReader
    txt = "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(txt, encoding="utf-8")
    return txt


def ingest_pdf(info: SourceInfo, text: str):
    refs = extract_refs({"t": text})
    retain = re.search(r"retain until\s+(\d{1,2} \w{3} \d{4})", text, re.I)
    base = {"retain_until": retain.group(1) if retain else None}
    for m in RESOURCE_RE.finditer(text):
        rid = m.group(0)
        attrs = dict(base)
        if re.search(r"\bfile\s+\S+\.pdf", text) and rid.startswith("support"):
            attrs["file"] = True
        info.facts.append(Fact(info.file_id, info.captured_at, info.captured_at, system_for_resource(rid), rid,
                               None, "FOUND", "primary", refs, attrs))
    for m in REGISTER_RE.finditer(text):  # finance register rows only confirm that a hold is active
        order, user, until = m.group(1), m.group(2).lower(), m.group(3)
        info.facts.append(Fact(info.file_id, info.captured_at, info.captured_at, "finance_register", None,
                               "LEGAL_HOLD_REGISTER", "FOUND", "primary", frozenset({user}),
                               {"register": True, "order": order, "retain_until": until}))
    for m in STATEMENT_RE.finditer(text):
        info.facts.append(Fact(info.file_id, info.captured_at, info.captured_at, "account_history_service",
                               m.group(0), "USER_PROFILE", "FOUND", "primary", refs, {"document": "statement"}))
    info.facts.append(Fact(info.file_id, info.captured_at, info.captured_at, "", None, None, None, "primary", refs,
                           {"document_text": text}))


# ---------------------------------------------------------------- images

STATE_WORDS = (("DISABLED", re.compile(r"\b(disabled|paused|stopped|inactive)\b", re.I)),
               ("ACTIVE", re.compile(r"\b(enabled|active|running|syncing)\b", re.I)))


def ingest_image(info: SourceInfo, path: Path, client):
    """Facts from screenshot tile transcripts: each listed id is an observed record; the panel links ids to identifiers."""
    cached = CACHE / "evidence" / f"{info.file_id}.json"
    if cached.exists():
        tiles = json.loads(cached.read_text(encoding="utf-8"))["tiles"]
    else:
        if client is None:
            info.skipped = "image not extracted (no model client / cache)"
            return
        import vision
        tiles = vision.transcribe(path, client, CACHE / "tiles")
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_text(json.dumps({"tiles": tiles}, sort_keys=True), encoding="utf-8")
    panel = tiles.get("panel", "")
    panel_refs = extract_refs({"t": panel})
    for name in sorted(tiles):
        text = tiles[name]
        units = [text] if name == "panel" else text.splitlines()
        for unit in units:
            refs = panel_refs if name == "panel" else extract_refs({"t": unit})
            for m in RESOURCE_RE.finditer(unit):
                rid = m.group(0)
                state = next((st for st, rx in STATE_WORDS if rx.search(unit)), "FOUND")
                sysid = system_for_resource(rid)
                info.facts.append(Fact(info.file_id, info.captured_at, info.captured_at, sysid, rid, None, state,
                                       "primary", refs, {"tile": name}))
                info.coverage[sysid] = max(info.coverage.get(sysid, ""), info.captured_at)
    if not info.facts:
        info.skipped = "screenshot shows no resource identifiers"


# ---------------------------------------------------------------- driver

def ingest_file(ef: EvidenceFile, client=None, base: Path = DATASET) -> SourceInfo:
    path = base / ef.file_path
    ext = path.suffix.lower()
    info = SourceInfo(ef.file_id, ef.captured_at, ef.file_path, ext.lstrip("."))
    if ext == ".sql":
        ingest_sql(info, path.read_text(encoding="utf-8"))
    elif ext == ".json":
        ingest_json(info, path.read_text(encoding="utf-8"))
    elif ext == ".log":
        ingest_log(info, path.read_text(encoding="utf-8"))
    elif ext == ".txt":
        ingest_text(info, path.read_text(encoding="utf-8"))
    elif ext == ".pdf":
        ingest_pdf(info, pdf_text(ef.file_id, path))
    elif ext == ".png":
        ingest_image(info, path, client)
    else:
        info.skipped = f"unsupported extension {ext}"
    return info


def ingest_all(manifest: Iterable[EvidenceFile], client=None) -> Dict[str, SourceInfo]:
    return {ef.file_id: ingest_file(ef, client) for ef in manifest}
