"""Repo-root-relative paths shared by all modules."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "dataset"
EVIDENCE = DATASET / "evidence"
CACHE = ROOT / ".cache"
PROMPTS = Path(__file__).resolve().parent / "prompts"
OUTPUT = ROOT / "output.csv"
EVAL_DIR = ROOT / "evaluation"
