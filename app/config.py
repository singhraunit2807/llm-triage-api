import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    llm_enabled: bool = os.getenv("LLM_ENABLED", "true").lower() == "true"
    llm_stub: bool = os.getenv("LLM_STUB", "0") == "1"
    api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    model: str = os.getenv("MODEL", "openrouter/free")
    timeout_seconds: float = min(float(os.getenv("LLM_TIMEOUT_SECONDS", "30")), 30.0)
    max_retries: int = max(0, int(os.getenv("MAX_RETRIES", "2")))
    prompt_version: str = os.getenv("PROMPT_VERSION", "v1")
    max_input_chars: int = min(int(os.getenv("MAX_INPUT_CHARS", "2000")), 2000)
    input_cost_per_1m: float = max(0.0, float(os.getenv("INPUT_COST_PER_1M", "0")))
    output_cost_per_1m: float = max(0.0, float(os.getenv("OUTPUT_COST_PER_1M", "0")))

settings = Settings()
