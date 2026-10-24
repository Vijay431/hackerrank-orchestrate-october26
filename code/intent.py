"""Request-intent gate: one cached LLM call per case decides if deletion is authorized."""
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Iterable, List

from llm import LLMClient
from loader import Activity, Request
import prompt_registry
from progress import Progress

WORKERS = 6
PROMPT = prompt_registry.load("intent")


def prior_classifications(req: Request, activity: Iterable[Activity], resource_ids: Iterable[str]) -> List[str]:
    """CLASSIFY_REQUEST events at or before audit_at for the given resources."""
    ids = set(resource_ids)
    return [a.details for a in activity
            if a.event_type == "CLASSIFY_REQUEST" and a.resource_id in ids and a.event_time <= req.audit_at]


def parse_decision(raw: str) -> bool:
    m = re.search(r"\{.*\}", raw, re.S)
    data = json.loads(m.group(0) if m else raw)
    val = data["authorizes_deletion"]
    if not isinstance(val, bool):
        raise ValueError("authorizes_deletion must be a boolean")
    return val


def classify(client: LLMClient, req: Request, context: List[str]) -> bool:
    text = f"request_text: {req.request_text}"
    if context:
        text += "\nprior_intake_classifications:\n" + "\n".join(f"- {c}" for c in sorted(context))
    return parse_decision(client.complete(PROMPT, text, purpose="intent"))


def classify_all(client: LLMClient, requests: List[Request], context_for) -> Dict[str, bool]:
    """Run classification in a 6-worker pool; results are keyed by case_id so order never matters."""
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {r.case_id: pool.submit(classify, client, r, context_for(r)) for r in requests}
        bar = Progress("intent", len(futures))
        for _ in as_completed(futures.values()):
            bar.update()
        bar.close()
        return {cid: f.result() for cid, f in futures.items()}
