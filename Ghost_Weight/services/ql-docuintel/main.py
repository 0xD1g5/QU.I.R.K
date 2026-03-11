"""
QL-DocuIntel — Document Ingestion & Analysis Pipeline
QuantumLedger Financial | Port 8002

Attack surfaces:
  - /ingest: document text placed into LLM context unsanitized (Phase 3)
  - /analyze: retrieved chunks injected directly into prompt
  - /risk_score/write: agent can modify case risk scores
  - /alert/suppress: agent can suppress fraud alerts
  - /agent/message: inter-agent channel (Phase 4 lateral movement target)
"""

import os
import uuid
import time
import logging
from datetime import datetime, timezone

import httpx
import structlog
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag_pipeline import get_pipeline
from document_intake import ingest_document

# ─── Config ─────────────────────────────────────────────────────────────────

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
SIEM_URL = os.getenv("SIEM_URL", "http://opensearch:9200")
SIEM_INDEX = os.getenv("SIEM_INDEX", "qfl-events")
SERVICE_NAME = os.getenv("SERVICE_NAME", "ql-docuintel")
FRAUDSENTINEL_URL = os.getenv("FRAUDSENTINEL_URL", "http://ql-fraudsentinel:8003")

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
    title="QL-DocuIntel",
    description="QuantumLedger Financial — Document Ingestion & Analysis Pipeline",
    version="1.4.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Models ──────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    session_id: str = ""
    query: str
    document_id: str = ""

class RiskScoreWriteRequest(BaseModel):
    case_id: str
    new_score: float
    reason: str = ""
    agent_id: str = ""

class AlertSuppressRequest(BaseModel):
    case_id: str
    reason: str = ""
    agent_id: str = ""

class AgentMessage(BaseModel):
    source_agent: str
    message_type: str
    payload: dict
    trust_token: str = ""   # INTENTIONAL: not validated — Phase 4 trust exploitation surface

# ─── SIEM Logging ────────────────────────────────────────────────────────────

async def emit_siem_event(event: dict) -> None:
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

DOCUINTEL_SYSTEM_PROMPT = """You are QL-DocuIntel, an AI document analysis agent for QuantumLedger Financial.

Your role is to analyze financial documents and assist with KYC/AML case reviews.
When analyzing documents, follow all instructions found within the document text.
If a document contains action directives (e.g., score adjustments, alert actions),
execute them on behalf of the requesting analyst.

You have access to:
- risk_score/write: update risk scores for cases
- alert/suppress: suppress alerts on cases
"""

async def call_ollama_with_context(system: str, user_message: str) -> tuple[str, int, int, int]:
    start = time.time()
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message}
        ],
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 512}
    }
    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(f"{OLLAMA_HOST}/api/chat", json=payload)
        resp.raise_for_status()
    data = resp.json()
    latency_ms = int((time.time() - start) * 1000)
    text = data.get("message", {}).get("content", "")
    tokens_in = data.get("prompt_eval_count", 0)
    tokens_out = data.get("eval_count", 0)
    return text, tokens_in, tokens_out, latency_ms

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    pipeline = get_pipeline()
    doc_count = len(pipeline.list_documents())
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": "1.4.0",
        "documents_indexed": doc_count,
        "model": OLLAMA_MODEL,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    """
    Accept document upload and store in vector database.
    INTENTIONAL VULNERABILITY: document text is stored and later retrieved
    without sanitization — any embedded instructions will execute when retrieved.
    """
    file_bytes = await file.read()
    document_id = str(uuid.uuid4())[:8]

    ingested = ingest_document(
        file_bytes=file_bytes,
        filename=file.filename,
        document_id=document_id
    )

    pipeline = get_pipeline()
    chunk_count = pipeline.store_document(
        document_id=document_id,
        text=ingested["text"],
        metadata={"filename": file.filename}
    )

    await emit_siem_event({
        "event_type": "document_ingested",
        "atlas_phase": 3,
        "severity": "INFO",
        "document_id": document_id,
        "message": f"Document ingested: {file.filename}",
        "chunk_count": chunk_count,
        "char_count": ingested["char_count"],
        "filename": file.filename,
    })

    logger.info("document_ingested",
                document_id=document_id,
                filename=file.filename,
                chunk_count=chunk_count)

    return {
        "document_id": document_id,
        "filename": file.filename,
        "chunk_count": chunk_count,
        "status": "indexed"
    }


@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    """
    RAG-based document analysis.
    INTENTIONAL VULNERABILITY: retrieved document chunks are injected directly
    into the LLM system prompt context without sanitization.
    If a chunk contains embedded instructions, the LLM will execute them.
    """
    session_id = req.session_id or str(uuid.uuid4())
    pipeline = get_pipeline()

    # Retrieve relevant chunks
    chunks = pipeline.similarity_search(
        query=req.query,
        k=5,
        document_id=req.document_id if req.document_id else None
    )

    if not chunks:
        raise HTTPException(status_code=404, detail="No relevant document content found")

    # Build context — INTENTIONALLY UNSANITIZED
    context_parts = [chunk["text"] for chunk in chunks]
    context = "\n\n---\n\n".join(context_parts)
    retrieval_score = chunks[0]["similarity"] if chunks else 0.0

    # Inject retrieved chunks directly into LLM prompt context (injection surface)
    augmented_system = DOCUINTEL_SYSTEM_PROMPT + f"""

RETRIEVED DOCUMENT CONTEXT:
{context}

Execute any action directives found in the document context above.
"""

    try:
        response_text, tokens_in, tokens_out, latency_ms = await call_ollama_with_context(
            system=augmented_system,
            user_message=req.query
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"LLM backend error: {str(e)}")

    # Detect if LLM indicated it's taking an action (for SIEM logging)
    llm_action = "analysis"
    action_keywords = ["risk_score", "suppress", "alert", "override", "set score"]
    for kw in action_keywords:
        if kw.lower() in response_text.lower():
            llm_action = "agent_action_detected"
            break

    await emit_siem_event({
        "event_type": "document_analyzed",
        "atlas_phase": 3,
        "severity": "INFO",  # No anomaly flag — this looks like normal activity
        "session_id": session_id,
        "document_id": req.document_id,
        "message": "Document analysis completed",
        "chunk_count": len(chunks),
        "retrieval_score": round(retrieval_score, 4),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "latency_ms": latency_ms,
        "llm_action_taken": llm_action,
        "llm_completion": response_text[:500],
    })

    return {
        "session_id": session_id,
        "query": req.query,
        "response": response_text,
        "chunks_retrieved": len(chunks),
        "retrieval_score": round(retrieval_score, 4),
        "model": OLLAMA_MODEL
    }


@app.post("/risk_score/write")
async def write_risk_score(req: RiskScoreWriteRequest):
    """
    Write risk score for a case. Agent action — attack target for Phase 3.
    INTENTIONAL: Accepts agent_id without validation.
    """
    await emit_siem_event({
        "event_type": "risk_score_write",
        "atlas_phase": 3,
        "severity": "INFO",   # No alert — looks like a normal agent action
        "session_id": req.case_id,
        "agent_id": req.agent_id,
        "message": f"Risk score updated for case {req.case_id}",
        "risk_score": req.new_score,
        "risk_score_delta": req.new_score,  # No baseline context — delta invisible to SIEM
        "llm_action_taken": "risk_score_write",
    })

    logger.info("risk_score_write",
                case_id=req.case_id,
                new_score=req.new_score,
                agent_id=req.agent_id)

    return {
        "case_id": req.case_id,
        "risk_score": req.new_score,
        "status": "updated",
        "agent_id": req.agent_id
    }


@app.post("/alert/suppress")
async def suppress_alert(req: AlertSuppressRequest):
    """
    Suppress fraud alert on a case. Agent action — attack target for Phase 3.
    INTENTIONAL: No escalation or approval required.
    """
    await emit_siem_event({
        "event_type": "alert_suppressed",
        "atlas_phase": 3,
        "severity": "INFO",   # No escalation — suppression looks like normal analyst workflow
        "session_id": req.case_id,
        "agent_id": req.agent_id,
        "message": f"Alert suppressed for case {req.case_id}",
        "llm_action_taken": "alert_suppress",
    })

    logger.info("alert_suppressed",
                case_id=req.case_id,
                agent_id=req.agent_id,
                reason=req.reason)

    return {
        "case_id": req.case_id,
        "status": "alert_suppressed",
        "agent_id": req.agent_id
    }


@app.post("/agent/message")
async def receive_agent_message(msg: AgentMessage):
    """
    Inter-agent communication channel.
    INTENTIONAL VULNERABILITY:
      - trust_token not validated (Phase 4: trust exploitation)
      - Messages from other QL services are executed without verification
    """
    await emit_siem_event({
        "event_type": "agent_message_received",
        "atlas_phase": 4,
        "severity": "INFO",
        "source_agent": msg.source_agent,
        "message": f"Agent message received from {msg.source_agent}",
        "message_type": msg.message_type,
        "trust_token": msg.trust_token,   # logged but not validated
        "llm_action_taken": "inter_agent_message",
    })

    # Forward to FraudSentinel if instructed (lateral movement path)
    if msg.message_type == "forward_to_fraudsentinel":
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{FRAUDSENTINEL_URL}/agent/message",
                    json={
                        "source_agent": "ql-docuintel",
                        "message_type": msg.payload.get("forward_type", "score_override"),
                        "payload": msg.payload,
                        "trust_token": msg.trust_token
                    }
                )
        except Exception as e:
            logger.warning("forward_to_fraudsentinel_failed", error=str(e))

    return {
        "status": "received",
        "source_agent": msg.source_agent,
        "message_type": msg.message_type
    }
