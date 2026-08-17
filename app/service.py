import json
import re
import time
from pathlib import Path
from .config import settings
from .models import TriageResponse, Category, Urgency
from .provider import get_provider, ProviderError

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "triage_v1.txt"
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
QUARANTINE = LOG_DIR / "quarantine.jsonl"
CALL_LOG = LOG_DIR / "calls.jsonl"

class ValidationFailure(Exception):
    pass

def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")

def parse_model_output(raw: str) -> TriageResponse:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I|re.S).strip()
    try:
        return TriageResponse.model_validate(json.loads(cleaned))
    except Exception as exc:
        raise ValidationFailure(str(exc)) from exc

def log_call(meta: dict, repair_count: int) -> None:
    entry = {"prompt_version":settings.prompt_version,"model":meta.get("model"),"input_tokens":meta.get("input_tokens",0),"output_tokens":meta.get("output_tokens",0),"duration_ms":meta.get("duration_ms",0),"repair_count":repair_count}
    with CALL_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False)+"\n")

def quarantine(text: str, raw: str, error: str) -> None:
    entry = {"input":text,"raw_model_output":raw,"error":error,"prompt_version":settings.prompt_version}
    with QUARANTINE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False)+"\n")

def deterministic_fallback() -> TriageResponse:
    return TriageResponse(category=Category.other, urgency=Urgency.low, confidence=0.1, reason="The LLM is disabled, so no confident category was assigned.")

def triage(text: str) -> TriageResponse:
    if not settings.llm_enabled:
        return deterministic_fallback()
    provider = get_provider()
    prompt = load_prompt()
    started = time.perf_counter()
    raw, meta = provider.complete(prompt, text)
    meta.setdefault("duration_ms", round((time.perf_counter()-started)*1000))
    try:
        result = parse_model_output(raw)
        log_call(meta, 0)
        return result
    except ValidationFailure as first_error:
        repair_prompt = prompt + "\nYour previous answer was invalid. Return only a valid JSON object matching the exact schema. Do not explain your correction."
        repair_raw, repair_meta = provider.complete(repair_prompt, text)
        repair_meta.setdefault("duration_ms", round((time.perf_counter()-started)*1000))
        try:
            result = parse_model_output(repair_raw)
            log_call(repair_meta, 1)
            return result
        except ValidationFailure as second_error:
            quarantine(text, repair_raw, f"initial={first_error}; repair={second_error}")
            raise ValidationFailure("Model output failed schema validation after one repair attempt")
