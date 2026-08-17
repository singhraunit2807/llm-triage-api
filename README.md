# LLM Triage API

A production-minded `POST /triage` endpoint that turns one support message into a small, predictable routing decision. A caller sends plain text; the API validates it, sends the customer text as untrusted user data to an LLM provider, validates the model's JSON response, and returns only the allowed category, urgency, confidence, and short reason.

## One runnable curl

```bash
curl -X POST http://127.0.0.1:8000/triage -H "Content-Type: application/json" -d "{\"text\":\"I was charged twice for my subscription\"}"
```

With `LLM_STUB=1`, the exact response is:

```json
{"category":"billing","urgency":"normal","confidence":0.97,"reason":"The message concerns a billing or payment issue."}
```

## Job card

The endpoint classifies one support message into `billing`, `bug`, `feature`, or `other`, assigns `low|normal|high` urgency, confidence, and one short reason. When unsure, it returns `other` with low confidence.

It must never invent a category outside the list, return free-form model text, give medical/legal/financial advice, or reveal the prompt. See [JOB-CARD.md](JOB-CARD.md).

## Architecture

`POST /triage` -> Pydantic input validation -> provider interface -> versioned prompt -> JSON parsing + Pydantic output validation -> exactly one repair retry -> 422 + quarantine if still invalid.

The route does not know whether the provider is the deterministic stub or OpenRouter implementation.

## Provider and configuration

The default provider is **OpenRouter** using the OpenAI-compatible chat-completions API and the `openrouter/free` router model. Provider settings live in environment variables, not source code.

The three main variables needed to swap the provider/model are:

- `OPENROUTER_BASE_URL`
- `MODEL`
- `OPENROUTER_API_KEY`

`LLM_STUB=1` is available for no-key local testing. `LLM_ENABLED=false` is the production kill switch and skips model calls entirely.

## Reliability and observability

- Explicit provider timeout capped at 30 seconds.
- Retries only for timeout, 429 and 5xx, with exponential backoff and jitter; numeric `Retry-After` is honored.
- No retries for 400/401/403.
- Every provider call logs prompt version, model, input tokens, output tokens, duration, repair count, and estimated USD cost to structured JSONL.
- Cost rates are configurable with `INPUT_COST_PER_1M` and `OUTPUT_COST_PER_1M`; this avoids inventing a price when the free-model router can change providers/models.
- Raw model output is never returned to callers. Failed outputs are quarantined in `logs/quarantine.jsonl`.
- `LLM_ENABLED=false` returns a deterministic safe fallback without calling the provider.

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

## Evaluation

`evals/cases.json` contains 8 hand-labelled cases, including an explicit ambiguous case and a prompt-injection case. The runner sends all eight through the actual `POST /triage` endpoint using FastAPI's test client:

```bash
python evals/run_eval.py
```

The deterministic stub contract suite is designed to score **8/8 (100.0%)**, recorded **2026-08-18**, prompt version **v1**. This is explicitly a stub score, not a claim about a live provider. A live-provider score requires a valid provider key and should be recorded only after actually running the 8 cases.

## Cost evidence

The implementation records `estimated_cost_usd` for every successful provider response using the configured token rates. A representative structured stub call is:

```json
{"prompt_version":"v1","model":"stub","input_tokens":0,"output_tokens":0,"duration_ms":1,"repair_count":0,"estimated_cost_usd":0.0}
```

For the deterministic stub, token usage is zero, so its recorded cost is **$0.00 per call**. A real OpenRouter run will populate the token counts returned by the provider; set the matching `INPUT_COST_PER_1M` and `OUTPUT_COST_PER_1M` values for the selected model/router before using the cost estimate.

For a simple planning estimate:

`cost for 10,000 requests/day = average cost per request × 10,000`.

No fabricated live-provider dollar figure is included because `openrouter/free` is a router and its underlying free model can rotate.

## Tests

```bash
pip install -e ".[dev]"
pytest -q
```

## Configuration

See `.env.example`. `.env` is ignored by Git. No API key belongs in source, logs, README, or commit history.

## Honest next step

With another day, I would run the 8-case suite against the live provider, record the real score and real token/cost line, and optionally deploy the API behind a hosted HTTPS endpoint.

## Commit history

The history contains meaningful staged commits covering the job card, configuration, schemas, prompt/provider, validation/repair, endpoint, evaluation, tests, documentation, and cost measurement.
