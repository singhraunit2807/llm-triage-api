# LLM Triage API

A production-minded `POST /triage` endpoint that puts an LLM behind a strict, gradeable API contract.

## Job card

The endpoint classifies one support message into `billing`, `bug`, `feature`, or `other`, assigns `low|normal|high` urgency, confidence, and one short reason. When unsure, it returns `other` with low confidence. See [JOB-CARD.md](JOB-CARD.md).

## Architecture

`POST /triage` -> Pydantic input validation -> provider interface -> versioned prompt -> JSON parsing + Pydantic output validation -> exactly one repair retry -> 422 + quarantine if still invalid.

The route does not know whether the provider is the stub or OpenRouter implementation.

## Reliability

- Explicit provider timeout capped at 30 seconds.
- Retries only for timeout, 429 and 5xx, with exponential backoff and jitter; numeric `Retry-After` is honored.
- No retries for 400/401/403.
- Every provider call logs prompt version, model, token counts, duration and repair count to structured JSONL.
- `LLM_ENABLED=false` disables model calls and returns a deterministic safe fallback.
- Raw model output is never returned to callers. Failed outputs are quarantined in `logs/quarantine.jsonl`.

## Safety

Customer text is always a separate user message and is treated as untrusted data. The prompt rejects prompt-injection instructions and prompt disclosure. The output is constrained by a closed enum schema.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -e .
copy .env.example .env
uvicorn app.main:app --reload
```

For a no-key smoke test, set `LLM_STUB=1` in `.env`.

### One runnable curl

```bash
curl -X POST http://127.0.0.1:8000/triage -H "Content-Type: application/json" -d "{\"text\":\"I was charged twice for my subscription\"}"
```

Example stub output:

```json
{"category":"billing","urgency":"normal","confidence":0.97,"reason":"The message concerns a billing or payment issue."}
```

## OpenRouter

The implementation uses the OpenAI-compatible OpenRouter chat-completions endpoint and defaults to `openrouter/free`. Put the key only in `.env`; never commit it.

## Evaluation

`evals/cases.json` contains 8 labelled cases. Run:

```bash
python evals/run_eval.py
```

Deterministic stub contract score: **8/8 (100.0%)**, recorded **2026-08-17**, prompt version **v1**. This is intentionally labelled as a stub score, not a live-provider model score.

## Tests

```bash
pip install -e ".[dev]"
pytest -q
```

## Configuration

See `.env.example`. `.env` is ignored by Git. No API key belongs in source, logs, README, or commit history.

## Commit history

The history is staged into meaningful commits covering the job card, configuration, schemas, prompt/provider, validation/repair, endpoint, evaluation, tests and documentation.
