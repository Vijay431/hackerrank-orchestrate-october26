"""Request-intent gate: one cached LLM call per case decides if deletion is authorized."""
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

from llm import LLMClient
from loader import Request
import prompt_registry
from progress import Progress

WORKERS = 6
PROMPT = prompt_registry.load("intent")


def parse_decision(raw: str) -> bool:
    m = re.search(r"\{.*\}", raw, re.S)
    data = json.loads(m.group(0) if m else raw)
    val = data["authorizes_deletion"]
    if not isinstance(val, bool):
        raise ValueError("authorizes_deletion must be a boolean")
    return val


def classify(client: LLMClient, req: Request) -> bool:
    # untrusted customer text: fence it so the prompt can tell data from instructions
    body = req.request_text.replace("<request_text>", "").replace("</request_text>", "")
    text = f"<request_text>\n{body}\n</request_text>"
    return parse_decision(client.complete(PROMPT, text, purpose="intent"))


def classify_all(client: LLMClient, requests: List[Request]) -> Dict[str, bool]:
    """Run classification in a 6-worker pool; results are keyed by case_id so order never matters."""
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {r.case_id: pool.submit(classify, client, r) for r in requests}
        bar = Progress("intent", len(futures))
        for _ in as_completed(futures.values()):
            bar.update()
        bar.close()
        return {cid: f.result() for cid, f in futures.items()}
