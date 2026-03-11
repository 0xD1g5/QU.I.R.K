"""
QL-Assist — AI Analyst Assistant Service
QuantumLedger Financial | Port 8001

Attack surfaces:
  - Direct prompt injection via /chat (Phase 1/2)
  - System prompt leakage via crafted queries
  - /admin endpoint exposes internal configuration (recon target)
  - /api/schema exposes full API surface (recon target)
"""

import os
import time
import uuid
import logging
from datetime import datetime, timezone

import httpx
import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from system_prompt import SYSTEM_PROMPT, SYSTEM_PROMPT_BRIEF

# ─── Config ─────────────────────────────────────────────────────────────────

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
SIEM_URL = os.getenv("SIEM_URL", "http://opensearch:9200")
SIEM_INDEX = os.getenv("SIEM_INDEX", "qfl-events")
SERVICE_NAME = os.getenv("SERVICE_NAME", "ql-assist")

# ─── Logging ─────────────────────────────────────────────────────────────────

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()

# ─── FastAPI App ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="QL-Assist",
    description="QuantumLedger Financial — AI Analyst Assistant",
    version="2.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Models ──────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str = ""
    user_id: str = "analyst"
    message: str


class ChatResponse(BaseModel):
    session_id: str
    response: str
    model: str
    tokens_in: int
    tokens_out: int
    latency_ms: int


# ─── SIEM Logging ────────────────────────────────────────────────────────────

async def emit_siem_event(event: dict) -> None:
    """POST structured event to OpenSearch SIEM index."""
    index_name = f"{SIEM_INDEX}-{datetime.now(timezone.utc).strftime('%Y.%m.%d')}"
    event.setdefault("@timestamp", datetime.now(timezone.utc).isoformat())
    event.setdefault("event_id", str(uuid.uuid4()))
    event["service"] = SERVICE_NAME

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(
                f"{SIEM_URL}/{index_name}/_doc",
                json=event,
                headers={"Content-Type": "application/json"}
            )
    except Exception as e:
        logger.warning("siem_emit_failed", error=str(e))


# ─── Ollama Inference ─────────────────────────────────────────────────────────

async def call_ollama(messages: list[dict]) -> tuple[str, int, int, int]:
    """
    Call Ollama chat API. Returns (response_text, tokens_in, tokens_out, latency_ms).
    Uses real LLM inference — no mocking.
    """
    start = time.time()
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 512}
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{OLLAMA_HOST}/api/chat", json=payload)
        resp.raise_for_status()

    data = resp.json()
    latency_ms = int((time.time() - start) * 1000)
    response_text = data.get("message", {}).get("content", "")
    tokens_in = data.get("prompt_eval_count", 0)
    tokens_out = data.get("eval_count", 0)
    return response_text, tokens_in, tokens_out, latency_ms


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": "2.1.0",
        "model": OLLAMA_MODEL,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/admin")
async def admin_panel():
    """
    Admin configuration endpoint.
    INTENTIONAL: This endpoint is a recon target — it exposes internal config.
    A real service would require authentication here.
    """
    return {
        "panel": "QL-Assist Administration",
        "version": "2.1.0",
        "environment": "production",
        "model_backend": OLLAMA_HOST,
        "active_model": OLLAMA_MODEL,
        "session_scope": "ANALYST_TIER2",
        "integrations": {
            "docuintel": "http://ql-docuintel:8002",
            "fraudsentinel": "http://ql-fraudsentinel:8003",
            "cms": "http://qfl-cms-internal:8090",
        },
        "config": {
            "max_tokens": 512,
            "temperature": 0.7,
            "prompt_version": "v2.1",
            "allow_external_instructions": True,
        },
        "note": "Contact ai.admin@quantumledger.com for access changes"
    }


@app.get("/api/schema")
async def api_schema():
    """
    API schema documentation.
    INTENTIONAL: Recon target — exposes full API surface to unauthenticated callers.
    """
    return {
        "service": "QL-Assist",
        "version": "2.1.0",
        "base_url": "http://ql-assist:8001",
        "endpoints": [
            {"method": "GET",  "path": "/health",      "auth": "none",     "description": "Health check"},
            {"method": "GET",  "path": "/admin",        "auth": "none",     "description": "Admin panel — configuration"},
            {"method": "GET",  "path": "/api/schema",   "auth": "none",     "description": "API documentation"},
            {"method": "POST", "path": "/chat",         "auth": "session",  "description": "LLM chat endpoint"},
        ],
        "model": OLLAMA_MODEL,
        "system_prompt_hint": SYSTEM_PROMPT_BRIEF,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    """
    Main LLM chat endpoint.
    INTENTIONAL VULNERABILITY: System prompt instructs the model to follow
    instructions from analyst requests, including from retrieved documents.
    This is the Phase 1/2 attack surface.
    """
    session_id = req.session_id or str(uuid.uuid4())

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": req.message}
    ]

    try:
        response_text, tokens_in, tokens_out, latency_ms = await call_ollama(messages)
    except httpx.HTTPError as e:
        await emit_siem_event({
            "event_type": "llm_error",
            "atlas_phase": 1,
            "severity": "HIGH",
            "session_id": session_id,
            "user_id": req.user_id,
            "message": f"Ollama call failed: {str(e)}",
        })
        raise HTTPException(status_code=503, detail="LLM backend unavailable")

    await emit_siem_event({
        "event_type": "chat_request",
        "atlas_phase": 1,
        "severity": "INFO",
        "session_id": session_id,
        "user_id": req.user_id,
        "message": f"Chat request processed",
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "latency_ms": latency_ms,
        "llm_completion": response_text[:500],  # truncated for index
    })

    logger.info("chat_request",
                session_id=session_id,
                user_id=req.user_id,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms)

    return ChatResponse(
        session_id=session_id,
        response=response_text,
        model=OLLAMA_MODEL,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=latency_ms
    )
