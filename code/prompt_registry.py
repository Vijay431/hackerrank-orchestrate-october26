"""Versioned prompts: prompts/<name>/<version>.txt, with the active version of each pinned here.

Bump a version by adding a new file and changing ACTIVE; old versions stay on disk for comparison.
The LLM cache key hashes the prompt text, so a new version never reuses responses from an old one.
"""
from paths import PROMPTS

ACTIVE = {
    "intent": "v2",
    "image_tile": "v1",
}


def load(name: str, version: str = "") -> str:
    version = version or ACTIVE[name]
    return (PROMPTS / name / f"{version}.txt").read_text(encoding="utf-8")
