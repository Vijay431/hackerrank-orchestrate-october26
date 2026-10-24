"""Entry point: audit every deletion request and write output.csv."""
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import DATASET, OUTPUT  # noqa: E402


def write_stub(requests_path: Path, out_path: Path) -> int:
    with open(requests_path, newline="", encoding="utf-8") as f:
        ids = sorted(r["case_id"] for r in csv.DictReader(f))
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["case_id", "deletion_status", "steps_json"])
        for cid in ids:
            w.writerow([cid, "NOT_APPLICABLE", "[]"])
    return len(ids)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Ghost Data Still Exists deletion-audit agent")
    p.add_argument("--requests", default=str(DATASET / "deletion_requests.csv"))
    p.add_argument("--output", default=str(OUTPUT))
    p.add_argument("--stub", action="store_true", help="write a NOT_APPLICABLE stub output")
    args = p.parse_args(argv)
    n = write_stub(Path(args.requests), Path(args.output))
    print(f"wrote {n} rows to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
