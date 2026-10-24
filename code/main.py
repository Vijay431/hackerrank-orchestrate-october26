"""Entry point: audit every deletion request and write output.csv."""
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import DATASET, OUTPUT  # noqa: E402
from progress import Progress  # noqa: E402


def write_rows(rows, out_path: Path):
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["case_id", "deletion_status", "steps_json"])
        for cid in sorted(rows):
            w.writerow([cid, *rows[cid]])


def audit(requests, intent, client):
    from identity import IdentityIndex
    import loader
    import ingest
    from state import ActivityLinker, FactIndex, link_resources, owners_map
    from policy import Policy
    from planner import assess, build_steps, serialize

    idx = IdentityIndex(loader.load_identities(), loader.load_audit_log())
    activity = loader.load_activity()
    findex = FactIndex(ingest.ingest_all(loader.load_evidence_manifest(), client))
    policy = Policy(loader.load_rules())
    universe = {r.case_id: r for r in list(loader.load_requests()) + list(loader.load_samples())}
    universe.update({r.case_id: r for r in requests})
    users, alias, seen = {}, {}, {}
    for r in sorted(universe.values(), key=lambda r: r.case_id):
        s = idx.resolve_email(r.email)
        if not s or not intent.get(r.case_id, True):  # a non-deletion request triggers no deletion-worker events
            continue
        rep = seen.setdefault((s.user_id, r.reported_at, r.audit_at), r.case_id)
        if rep == r.case_id:
            users[r.case_id] = s.user_id
        else:  # repeat request from the same person at the same time: shares the first request's links
            alias[r.case_id] = rep
    linker = ActivityLinker([r for r in universe.values() if r.case_id in users], users,
                            owners_map(findex, idx), activity)
    rows = {}
    bar = Progress("audit", len(requests))
    for r in requests:
        bar.update()
        if not intent.get(r.case_id, False):
            rows[r.case_id] = ("NOT_APPLICABLE", "[]")
            continue
        subject = idx.resolve_email(r.email)
        if subject is None:
            rows[r.case_id] = ("NOT_APPLICABLE", "[]")
            continue
        vals = subject.values()
        links = link_resources(r, vals, findex, activity, linker, alias.get(r.case_id, r.case_id))
        items = [it for it in (assess(l, r.audit_at, vals, findex, policy) for l in links.values()) if it]
        status, steps = build_steps(items)
        rows[r.case_id] = (status, serialize(steps))
    bar.close()
    if policy.unresolved:
        print(f"warning: {policy.unresolved} resource categories could not be resolved", file=sys.stderr)
    return rows


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Ghost Data Still Exists deletion-audit agent")
    p.add_argument("--requests", default=str(DATASET / "deletion_requests.csv"))
    p.add_argument("--output", default=str(OUTPUT))
    p.add_argument("--stub", action="store_true", help="write a NOT_APPLICABLE stub output")
    p.add_argument("--assume-deletion", action="store_true",
                   help="development only: skip the LLM intent gate and treat every request as a deletion request")
    args = p.parse_args(argv)

    import loader
    requests = sorted(loader.load_requests(Path(args.requests)), key=lambda r: r.case_id)
    if args.stub:
        write_rows({r.case_id: ("NOT_APPLICABLE", "[]") for r in requests}, Path(args.output))
        print(f"wrote {len(requests)} stub rows to {args.output}")
        return 0

    client = None
    if args.assume_deletion:
        intent = {r.case_id: True for r in requests}
    else:
        from llm import LLMClient
        from intent import classify_all
        client = LLMClient()
        activity = loader.load_activity()
        # every known request, so events cannot be attributed to a case that asked for something else
        everyone = {r.case_id: r for r in list(loader.load_requests()) + list(loader.load_samples()) + requests}
        intent = classify_all(client, sorted(everyone.values(), key=lambda r: r.case_id), lambda r: [])
    rows = audit(requests, intent, client)
    write_rows(rows, Path(args.output))
    print(f"wrote {len(rows)} rows to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
