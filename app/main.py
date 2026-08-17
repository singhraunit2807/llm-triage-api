from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from .config import settings
from .models import TriageRequest, TriageResponse
from .service import triage, ValidationFailure
from .provider import ProviderError

app = FastAPI(title="LLM Triage API", version="0.1.0")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(status_code=400, content={"error":"invalid_input", "detail":exc.errors()})

@app.post("/triage", response_model=TriageResponse)
def triage_endpoint(payload: TriageRequest):
    if len(payload.text) > settings.max_input_chars:
        raise HTTPException(status_code=400, detail=f"text exceeds {settings.max_input_chars} characters")
    try:
        return triage(payload.text)
    except ValidationFailure as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except ProviderError as exc:
        if exc.timeout:
            raise HTTPException(status_code=504, detail="LLM provider timed out")
        if exc.status_code == 429 or (exc.status_code and 500 <= exc.status_code < 600):
            raise HTTPException(status_code=503, detail="LLM provider temporarily unavailable")
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=502, detail="LLM provider request failed")

@app.get("/health")
def health():
    return {"status":"ok", "llm_enabled":settings.llm_enabled, "stub":settings.llm_stub}
