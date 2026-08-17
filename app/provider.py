import json
import random
import time
from typing import Protocol
import httpx
from .config import settings

class ProviderError(Exception):
    def __init__(self, message: str, status_code: int | None = None, retryable: bool = False, timeout: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable
        self.timeout = timeout

class Provider(Protocol):
    def complete(self, prompt: str, text: str) -> tuple[str, dict]: ...

class StubProvider:
    def complete(self, prompt: str, text: str) -> tuple[str, dict]:
        t = text.lower()
        if any(x in t for x in ["charged", "charge", "invoice", "refund", "payment", "subscription"]):
            result = {"category":"billing","urgency":"normal","confidence":0.97,"reason":"The message concerns a billing or payment issue."}
        elif any(x in t for x in ["outage", "down for everyone", "security breach", "data loss", "every user"]):
            result = {"category":"bug","urgency":"high","confidence":0.98,"reason":"The message describes a severe product failure."}
        elif any(x in t for x in ["error", "500", "crash", "broken", "not working", "fails", "failed"]):
            result = {"category":"bug","urgency":"normal","confidence":0.96,"reason":"The message describes an existing product problem."}
        elif any(x in t for x in ["please add", "would like", "feature", "support", "can you add", "request"]):
            result = {"category":"feature","urgency":"low","confidence":0.92,"reason":"The message asks for a new capability or improvement."}
        else:
            result = {"category":"other","urgency":"low","confidence":0.55,"reason":"The message does not clearly fit the supported categories."}
        return json.dumps(result), {"model":"stub", "input_tokens":0, "output_tokens":0}

class OpenRouterProvider:
    def complete(self, prompt: str, text: str) -> tuple[str, dict]:
        if not settings.api_key:
            raise ProviderError("OPENROUTER_API_KEY is not configured", status_code=401, retryable=False)
        payload = {"model": settings.model, "messages":[{"role":"system","content":prompt},{"role":"user","content":text}], "temperature":0, "max_tokens":220}
        headers = {"Authorization": f"Bearer {settings.api_key}", "Content-Type":"application/json"}
        for attempt in range(settings.max_retries + 1):
            started = time.perf_counter()
            try:
                with httpx.Client(timeout=settings.timeout_seconds) as client:
                    response = client.post(f"{settings.base_url.rstrip('/')}/chat/completions", headers=headers, json=payload)
                if response.status_code == 429 or 500 <= response.status_code < 600:
                    retry_after = response.headers.get("Retry-After")
                    if attempt < settings.max_retries:
                        numeric_retry_after = retry_after and retry_after.replace('.', '', 1).isdigit()
                        delay = float(retry_after) if numeric_retry_after else min(4.0, 2 ** attempt) + random.uniform(0, .25)
                        time.sleep(delay)
                        continue
                    raise ProviderError(f"provider returned {response.status_code}", response.status_code, retryable=True)
                if response.status_code in (400,401,403):
                    raise ProviderError(f"provider returned {response.status_code}", response.status_code, retryable=False)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage") or {}
                return content, {"model":data.get("model",settings.model), "input_tokens":usage.get("prompt_tokens",0), "output_tokens":usage.get("completion_tokens",0), "duration_ms":round((time.perf_counter()-started)*1000)}
            except httpx.TimeoutException as exc:
                if attempt < settings.max_retries:
                    time.sleep(min(4.0, 2 ** attempt) + random.uniform(0, .25))
                    continue
                raise ProviderError("LLM request timed out", timeout=True, retryable=True) from exc
            except httpx.HTTPError as exc:
                raise ProviderError(str(exc), retryable=False) from exc
        raise ProviderError("LLM provider request failed")

def get_provider() -> Provider:
    if settings.llm_stub or not settings.llm_enabled:
        return StubProvider()
    return OpenRouterProvider()
