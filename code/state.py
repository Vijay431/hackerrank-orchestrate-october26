"""Fact index, resource linking, and resource state at audit_at.

Reported statuses and activity results are claims; state comes only from the
latest evidence observation at or before audit_at.
"""
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Set

from ingest import RESOURCE_RE, EMAIL_RE, Fact, SourceInfo, system_for_resource, USER_RE
from loader import Activity, Request

# Sources whose records are complete dumps: omission of a resource proves absence.
SNAPSHOT_KINDS = {"sql"}
PRESENT_STATES = {"FOUND", "IDENTIFIABLE", "PRESENT", "ACTIVE"}
ABSENT_STATES = {"NOT_FOUND", "ABSENT"}
ANCHOR_WINDOW = (timedelta(minutes=-10), timedelta(minutes=30))


def _t(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


class FactIndex:
    def __init__(self, sources: Dict[str, SourceInfo]):
        self.sources = sources
        self.by_resource: Dict[str, List[Fact]] = defaultdict(list)
        self.by_ref: Dict[str, List[Fact]] = defaultdict(list)
        for info in sources.values():
            for f in info.facts:
                if f.resource_id:
                    self.by_resource[f.resource_id].append(f)
                for r in f.refs:
                    self.by_ref[r].append(f)


@dataclass
class Observation:
    state: str                      # FOUND/IDENTIFIABLE/ACTIVE/... or ABSENT
    source_id: str                  # evidence file_id, or "" when only activity supports it
    observed_at: str
    fact: Optional[Fact] = None
    by_omission: bool = False


@dataclass
class Linked:
    resource_id: str
    system_id: str
    reasons: Set[str] = field(default_factory=set)
    activity_ids: List[str] = field(default_factory=list)


def link_resources(req: Request, identity_values: frozenset, index: FactIndex,
                   activity: Iterable[Activity], linker: "ActivityLinker" = None,
                   linker_case: str = None) -> Dict[str, Linked]:
    cutoff = req.audit_at
    out: Dict[str, Linked] = {}

    def add(rid, reason, system=None, act_id=None):
        system = system or system_for_resource(rid)
        if not system:
            return
        item = out.setdefault(rid, Linked(rid, system))
        item.reasons.add(reason)
        if act_id:
            item.activity_ids.append(act_id)

    # 1. evidence that names an identifier of the subject
    linked_facts: List[Fact] = []
    for v in identity_values:
        for f in index.by_ref.get(v, ()):
            # a lookup that found nothing before the request was made answers an earlier request
            stale = f.state in ABSENT_STATES and f.observed_at < req.requested_at
            if f.resource_id and f.observed_at <= cutoff and not stale:
                add(f.resource_id, "evidence", f.system_id)
                linked_facts.append(f)
    # 2. resources referenced by linked records (e.g. a search document's source account)
    for f in linked_facts:
        for k, v in f.attrs.items():
            if k.endswith("source_resource_id") and isinstance(v, str) and RESOURCE_RE.fullmatch(v):
                add(v, "derived")
    # 3. data catalog link events and narrative deletion-worker events
    for a in activity:
        if a.event_time > cutoff:
            continue
        if a.event_type == "LINK_RESOURCE_IDENTITY":
            low = a.details.lower()
            if any(v in low for v in identity_values if "@" in v or v.startswith("user_")):
                if index.by_resource.get(a.resource_id):  # a catalog link alone proves nothing about state
                    add(a.resource_id, "catalog", a.target_system, a.activity_id)
    if linker is not None:
        for rid, act_id in linker.resources_for(linker_case or req.case_id).items():
            add(rid, "activity", linker.system.get(rid), act_id)
    # 4. no account linked: account ids mirror the user number (account_005 <-> user_05 in every
    #    account snapshot row), so check that id, and keep it only when a snapshot proves it absent
    if not any(l.system_id == "account_service" for l in out.values()):
        for v in sorted(identity_values):
            m = re.fullmatch(r"user_(\d{1,2})", v)
            rid = m and f"account_{int(m.group(1)):03d}"
            obs = rid and observe(rid, "account_service", cutoff, index)
            if obs and obs.by_omission:
                add(rid, "convention", "account_service")
                break
    return out


def observe(rid: str, system_id: str, audit_at: str, index: FactIndex) -> Optional[Observation]:
    """State of a resource at audit_at across all stores that hold or could hold a copy.

    Each store (a capture family such as a replica or the primary dump) is
    reduced to its latest observation at or before audit_at. A copy that
    remains in any store counts as present; otherwise the resource is absent.
    """
    per_store: Dict[str, tuple] = {}  # store -> ((observed_at, explicit, captured_at), Observation)

    def offer(store, key, obs):
        if store not in per_store or key > per_store[store][0]:
            per_store[store] = (key, obs)

    for f in index.by_resource.get(rid, ()):
        if f.observed_at > audit_at or f.captured_at > audit_at or not f.state:
            continue
        info = index.sources[f.source_id]
        offer(info.store, (f.observed_at, 1, f.captured_at), Observation(f.state, f.source_id, f.observed_at, f))
    for info in index.sources.values():
        if info.captured_at > audit_at:
            continue
        for snap in info.snaps:
            if snap.system_id == system_id and snap.time <= audit_at and rid not in snap.resources:
                # a snapshot file holding no record at all proves little: rank it below one that does
                offer(info.store, (snap.time, 0.5 if info.facts else 0, info.captured_at),
                      Observation("ABSENT", info.file_id, snap.time, None, True))
    if not per_store:
        return None
    present = [v for v in per_store.values() if v[1].state in PRESENT_STATES]
    pool = present or list(per_store.values())

    def pref(v):  # prefer explicit observations, then the most recent
        return (v[0][1], v[0][0], v[0][2])
    return max(pool, key=pref)[1]


# ---------------------------------------------------------------- activity linking

POLICY_SLOTS = [  # (event_type, target_system, min offset, max offset) relative to reported_at, minutes
    ("ANONYMIZE_RECORD", "analytics_platform", -30, -27),
    ("REDACT_RECORD", "support_platform", -23, -20),
    ("REDACT_RECORD", "identity_service", -30, -26),
    ("DISABLE_DATA_FLOW", "integration_service", -16, -13),
    ("BLOCK_RESTORE", "backup_service", -9, -6),
]
ACCOUNT_WINDOW = (-76.0, -44.0)
RESULTS_FOR_STATUS = {"COMPLETE": ("SUCCESS",), "NOT_STARTED": ("FAILED",), "PARTIALLY_COMPLETE": ("PARTIAL", "SUCCESS")}
NARRATIVE_WINDOW = (-10.0, 30.0)


def _mins(a: str, b: str) -> float:
    return (_t(a) - _t(b)).total_seconds() / 60.0


ACCOUNT_LEAD_SECONDS = (22, 41, 52)  # seconds past a whole minute between an account step and the next one


def _gap_phase(later: datetime, earlier: datetime) -> bool:
    sec = int((later - earlier).total_seconds()) % 60
    return any(abs(sec - x) <= 1 for x in ACCOUNT_LEAD_SECONDS)


FIRST_ACTIONS = ("analytics_platform", "identity_service")
POLICY_LEAD_SECONDS = 41


CHAIN = ["analytics_platform", "support_platform", "integration_service", "backup_service"]
CHAIN_GAP = (6.0, 9.0)  # minutes between consecutive policy actions of one case
CHAIN_STEPS = (6.5, 449 / 60)  # gaps cluster at 390 s and 449 s; prefer the candidate nearest one of them


class ActivityLinker:
    """Ties deletion-worker events to cases by their timing relative to reported_at.

    Events carry no subject identifier, so ownership comes from (a) evidence that
    already ties a resource to a subject, (b) the fixed time slots policy actions
    occupy before the report and the regular gap between consecutive actions of
    one case, and (c) elimination: a case holds at most one event per slot, and an
    event with a single possible owner belongs to that owner.
    """

    def __init__(self, universe: List[Request], user_of_case: Dict[str, str], owners: Dict[str, Set[str]],
                 activity: Iterable[Activity]):
        cases = {r.case_id: r for r in universe}
        self.by_case: Dict[str, Dict[str, str]] = {c: {} for c in cases}
        acts = [a for a in activity if a.source_system == "deletion_worker"]
        self.system = {a.resource_id: a.target_system for a in acts}
        pol = [a for a in acts if "Policy action completed" in a.details]
        owner_case: Dict[str, str] = {}   # event resource -> case id

        def foreign(rid, cid):
            o = owners.get(rid)
            return bool(o) and user_of_case[cid] not in o

        def in_slot(a, r):
            d = _mins(a.event_time, r.reported_at)
            return any(a.event_type == et and a.target_system == sy and lo <= d <= hi
                       for et, sy, lo, hi in POLICY_SLOTS) and a.event_time <= r.audit_at

        def slot_of(a):
            return a.target_system

        def assign(a, cid):
            owner_case[a.resource_id] = cid
            self.by_case[cid][a.resource_id] = a.activity_id

        def holds(cid, system):
            return any(self.system.get(x) == system for x in self.by_case[cid]) or \
                any(self.system.get(rid) == system and user_of_case[cid] in owners.get(rid, ())
                    for rid in self.system)

        after_cache: Dict[str, bool] = {}

        def after_report(cid):
            """The case already has worker results from after its report: it is not a policy-action case."""
            if cid not in after_cache:
                after_cache[cid] = _after_report(cid)
            return after_cache[cid]

        def _after_report(cid):
            r = cases[cid]
            return any(a.event_time > r.reported_at and "Policy action" not in a.details
                       and a.target_system != "account_service" and user_of_case[cid] in owners.get(a.resource_id, ())
                       for a in acts)

        def too_close(cid, a):
            """One case's policy actions are at least a chain gap apart."""
            return any(b is not a and (owner_case.get(b.resource_id) == cid or user_of_case[cid] in owners.get(b.resource_id, ()))
                       and abs(_mins(a.event_time, b.event_time)) < CHAIN_GAP[0] for b in pol)

        # anchors: events whose resource evidence ties to the case's subject
        by_user = defaultdict(list)
        for cid in cases:
            by_user[user_of_case[cid]].append(cid)
        for a in pol:
            for u in owners.get(a.resource_id, ()):
                for cid in by_user.get(u, ()):
                    if in_slot(a, cases[cid]):
                        assign(a, cid)
        changed = True
        while changed:
            changed = False
            # chains: other actions of the same case follow an anchored action by one regular gap
            for cid in cases:
                mine = [a for a in pol if owner_case.get(a.resource_id) == cid]
                for anchor in mine:
                    k = CHAIN.index(anchor.target_system) if anchor.target_system in CHAIN else None
                    if k is None:
                        continue
                    best: Dict[str, tuple] = {}
                    for a in pol:
                        if a.resource_id in owner_case or a.target_system not in CHAIN or foreign(a.resource_id, cid):
                            continue
                        hops = CHAIN.index(a.target_system) - k
                        if hops == 0 or not in_slot(a, cases[cid]) or holds(cid, a.target_system):
                            continue
                        gap = _mins(a.event_time, anchor.event_time)
                        lo, hi = sorted((hops * CHAIN_GAP[0], hops * CHAIN_GAP[1]))
                        if lo <= gap <= hi:
                            dev = min(abs(gap - hops * step) for step in CHAIN_STEPS)
                            if a.target_system not in best or dev < best[a.target_system][0]:
                                best[a.target_system] = (dev, a)
                    for _, a in best.values():
                        assign(a, cid)
                        changed = True
            # elimination: a single remaining candidate owner takes the event
            for a in pol:
                if a.resource_id in owner_case:
                    continue
                cands = [cid for cid, r in cases.items() if in_slot(a, r) and not foreign(a.resource_id, cid)
                         and not holds(cid, a.target_system) and not after_report(cid)
                         and not too_close(cid, a)]
                if len(cands) == 1:
                    assign(a, cands[0])
                    changed = True

        # equal numbers of unclaimed events and candidate cases in one slot: pair them in order
        for system in CHAIN + ["identity_service"]:
            free = [a for a in pol if a.target_system == system and a.resource_id not in owner_case]
            groups: Dict[frozenset, List[Activity]] = defaultdict(list)
            for a in free:
                cs = frozenset(cid for cid, r in cases.items() if in_slot(a, r) and not foreign(a.resource_id, cid)
                               and not holds(cid, system))
                if cs:
                    groups[cs].append(a)
            for cs, evs in groups.items():
                if len(evs) == len(cs):
                    for a, cid in zip(sorted(evs, key=lambda x: x.event_time), sorted(cs)):
                        assign(a, cid)

        # narrative events (explicit "Target resource" templates) near the report time
        for a in acts:
            if "Target resource:" in a.details:
                cands = [cid for cid, r in cases.items()
                         if NARRATIVE_WINDOW[0] <= _mins(a.event_time, r.reported_at) <= NARRATIVE_WINDOW[1]
                         and a.event_time <= r.audit_at and not foreign(a.resource_id, cid)]
                if len(cands) == 1:
                    self.by_case[cands[0]][a.resource_id] = a.activity_id

        # accounts: one per case, found by elimination over the report-time window
        acc = [a for a in acts if a.event_type == "DELETE_RECORD" and a.target_system == "account_service"
               and "submitted primary profile" in a.details]
        taken: Dict[str, str] = {}
        done: Dict[str, Activity] = {}
        for cid in cases:
            if any(self.system.get(x) == "account_service" for x in self.by_case[cid]):
                continue
            have = [a for a in acc if user_of_case[cid] in owners.get(a.resource_id, ())]
            if have:
                done[cid] = have[0]
                taken[have[0].resource_id] = cid
        cand = {}
        for cid in cases:
            if cid in done or any(self.system.get(x) == "account_service" for x in self.by_case[cid]):
                continue
            r = cases[cid]
            opts = [a for a in acc if ACCOUNT_WINDOW[0] <= _mins(a.event_time, r.reported_at) <= ACCOUNT_WINDOW[1]
                    and a.event_time <= r.audit_at and not foreign(a.resource_id, cid)]
            # the worker's result tracks the status the workflow reported; use it when it still leaves a choice
            opts = [a for a in opts if a.reported_result in RESULTS_FOR_STATUS.get(r.reported_status, ())] or opts
            # the worker runs a case's account step a whole number of minutes plus a fixed offset
            # before its next recorded action, so that offset separates look-alike candidates
            nxt = [_t(a.event_time) for a in acts if a.target_system != "account_service" and a.event_time <= r.audit_at
                   and (a.resource_id in self.by_case[cid] or user_of_case[cid] in owners.get(a.resource_id, ()))]
            if nxt:
                opts = [a for a in opts if _gap_phase(min(nxt), _t(a.event_time))] or opts
            cand[cid] = opts
        progress = True
        while cand and progress:
            progress = False
            for cid in sorted(cand, key=lambda c: (len(cand[c]), cases[c].reported_at, c)):
                opts = [a for a in cand[cid] if a.resource_id not in taken]
                if len(opts) == 1:
                    taken[opts[0].resource_id] = cid
                    done[cid] = opts[0]
                    del cand[cid]
                    progress = True
                    break
        for cid in sorted(cand, key=lambda c: (cases[c].reported_at, c)):  # fallback: earliest free event
            opts = sorted((a for a in cand[cid] if a.resource_id not in taken), key=lambda a: a.event_time)
            if opts:
                taken[opts[0].resource_id] = cid
                done[cid] = opts[0]
        for cid, a in done.items():
            self.by_case[cid][a.resource_id] = a.activity_id

        # a case's first policy action follows its account step by whole minutes plus a fixed offset
        for cid, a in done.items():
            for e in pol:
                if e.resource_id in owner_case or e.target_system not in FIRST_ACTIONS or holds(cid, e.target_system) \
                        or not in_slot(e, cases[cid]) or foreign(e.resource_id, cid):
                    continue
                if abs(int((_t(e.event_time) - _t(a.event_time)).total_seconds()) % 60 - POLICY_LEAD_SECONDS) <= 1 \
                        and sum(1 for c2, a2 in done.items() if c2 != cid and in_slot(e, cases[c2]) and abs(
                            int((_t(e.event_time) - _t(a2.event_time)).total_seconds()) % 60 - POLICY_LEAD_SECONDS) <= 1) == 0:
                    assign(e, cid)

    def resources_for(self, case_id: str) -> Dict[str, str]:
        return self.by_case.get(case_id, {})


def owners_map(index: FactIndex, identity_index) -> Dict[str, Set[str]]:
    """resource_id -> user_ids that evidence ties it to."""
    out: Dict[str, Set[str]] = defaultdict(set)
    for rid, facts in index.by_resource.items():
        for f in facts:
            for r in f.refs:
                u = identity_index.user_of_value(r)
                if u:
                    out[rid].add(u)
    return out
