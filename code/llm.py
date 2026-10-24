"""OpenRouter client for the single allowed model, with a disk cache and usage ledger.

The API key is read from OPENROUTER_API_KEY at call time and is never written
to the cache, the ledger, or any log.
"""
import base64
import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from paths import CACHE, ROOT

MODEL = "deepseek/deepseek-v4.1-flash"
PROVIDER = "openrouter"
CACHE_DIR = CACHE / "llm"
LEDGER = CACHE / "usage_ledger.jsonl"
MAX_ATTEMPTS = 4
_ledger_lock = threading.Lock()


class LLMError(RuntimeError):
    pass


def cache_key(model: str, prompt: str, payload: str) -> str:
    h = hashlib.sha256()
    for part in (model, prompt, payload):
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def _dotenv_value(name: str) -> Optional[str]:
    """Read one value from the repo-root .env as literal text: no expansion, no command substitution."""
    path = ROOT / ".env"
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        k, sep, v = line.partition("=")
        if sep and k.strip() == name:
            return v.strip().strip("\"'") or None
    return None


def _openrouter_transport(prompt: str, text: str, image_path: Optional[Path]):
    """Real call through the OpenRouter SDK. Returns (content, input_tokens, output_tokens)."""
    key = os.environ.get("OPENROUTER_API_KEY") or _dotenv_value("OPENROUTER_API_KEY")
    if not key:
        raise LLMError("OPENROUTER_API_KEY is not set and no cached response exists")
    from openrouter import OpenRouter

    user_content = [{"type": "text", "text": text}]
    if image_path is not None:
        b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
        user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
    with OpenRouter(api_key=key) as client:
        res = client.chat.send(
            model=MODEL,
            temperature=0,
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_content}],
            stream=False,
        )
    content = res.choices[0].message.content
    if not isinstance(content, str) or not content.strip():
        raise ValueError("empty model response")  # transient: retried by the client, never cached
    usage = res.usage
    return content, int(getattr(usage, "prompt_tokens", 0) or 0), int(getattr(usage, "completion_tokens", 0) or 0)


Transport = Callable[[str, str, Optional[Path]], tuple]


class LLMClient:
    def __init__(self, transport: Transport = _openrouter_transport, cache_dir: Path = CACHE_DIR,
                 ledger: Path = LEDGER, sleep: Callable[[float], None] = time.sleep):
        self.transport = transport
        self.cache_dir = cache_dir
        self.ledger = ledger
        self.sleep = sleep

    def _record(self, kind: str, purpose: str, cache_hit: bool, tin: int, tout: int):
        entry = {"provider": PROVIDER, "model": MODEL, "purpose": purpose,
                 "cache_hit": cache_hit, "input_tokens": tin, "output_tokens": tout}
        with _ledger_lock:
            self.ledger.parent.mkdir(parents=True, exist_ok=True)
            with open(self.ledger, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, sort_keys=True) + "\n")

    def complete(self, prompt: str, text: str, image_path: Optional[Path] = None,
                 purpose: str = "") -> str:
        """Return the model response, from cache when the same model/prompt/input was seen."""
        payload = text
        if image_path is not None:
            payload += "\x00" + hashlib.sha256(image_path.read_bytes()).hexdigest()
        key = cache_key(MODEL, prompt, payload)
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            cached = json.loads(path.read_text(encoding="utf-8"))
            self._record("llm", purpose, True, 0, 0)
            return cached["response"]
        last = None
        for attempt in range(MAX_ATTEMPTS):
            try:
                content, tin, tout = self.transport(prompt, text, image_path)
                break
            except LLMError:
                raise
            except Exception as e:  # transient failure: back off, never cache
                last = e
                self.sleep(min(2 ** attempt, 8))
        else:
            raise LLMError(f"model call failed after {MAX_ATTEMPTS} attempts: {type(last).__name__}")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".{threading.get_ident()}.tmp")
        tmp.write_text(json.dumps({"model": MODEL, "response": content}, sort_keys=True), encoding="utf-8")
        tmp.replace(path)
        self._record("llm", purpose, False, tin, tout)
        return content
