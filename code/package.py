"""Build code.zip (runnable solution, prompts, config, README, evaluation reports) and list its contents.

Excluded: dataset/, .cache/, virtual environments, caches, .env files, output.csv, log.txt.
"""
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import ROOT  # noqa: E402

INCLUDE = ["code", "README.md", ".env.example", "evaluation", "tests"]
SKIP_PARTS = {"__pycache__", ".pytest_cache", ".venv", "venv", ".cache", "dataset", "node_modules"}


def files():
    for item in INCLUDE:
        p = ROOT / item
        if p.is_file():
            yield p
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                skipped = set(f.relative_to(ROOT).parts) & SKIP_PARTS or f.suffix in {".pyc", ".zip"}
                secret = f.name.startswith(".env") and f.name != ".env.example"
                if f.is_file() and not skipped and not secret:
                    yield f


def main():
    out = ROOT / "code.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files():
            z.write(f, f.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
    bad = [n for n in names if n.startswith(("dataset/", ".cache/")) or n.endswith((".env", ".zip", ".pyc"))
           or "/.venv/" in n or n.startswith(".venv/")]
    print("\n".join(names))
    print(f"{len(names)} files; excluded-content violations: {bad or 'none'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
