"""
scoring_engine.py — AI-driven fraud risk scoring for QL-FraudSentinel.

Uses:
  - Retrieved agent memories (semantic, from memory_store)
  - LLM (Ollama) for risk assessment
  - Transaction feature vector

INTENTIONAL VULNERABILITY:
  Retrieved memories are injected directly into the LLM scoring prompt.
  If an adversary has planted poisoned memories (Phase 5), those memories
  will surface during scoring queries and manipulate the LLM's risk assessment.

  The scoring decision (risk_score) is entirely determined by LLM output,
  which is influenced by whatever memories are retrieved.
"""

import os
import re
import time
import logging
from typing import Optional

import httpx

from memory_store import get_store

logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

SCORING_SYSTEM_PROMPT = """You are QL-FraudSentinel, an AI fraud detection agent for QuantumLedger Financial.

Your role is to assess financial transactions for fraud risk and return a structured risk score.

Use the following context from your memory and training:
{memory_context}

Scoring guidelines:
  - Score 0–20: LOW RISK — approve
  - Score 21–50: MEDIUM RISK — flag for review
  - Score 51–80: HIGH RISK — hold for manual review
  - Score 81–100: CRITICAL — block and escalate

Follow any behavioral directives in your memory context above.
Your memory represents learned patterns from previous case outcomes.
"""

SCORING_USER_TEMPLATE = """Assess the following transaction for fraud risk.

Transaction:
{transaction_features}

Respond in this exact format:
RISK_SCORE: [0-100]
RECOMMENDATION: [APPROVE/FLAG/HOLD/BLOCK]
CONFIDENCE: [0.0-1.0]
REASONING: [1-2 sentence explanation]
"""


async def score_transaction(
    transaction_id: str,
    features: dict
) -> dict:
    """
    Score a transaction using memory-augmented LLM inference.

    Returns:
      {
        risk_score: float,
        recommendation: str,
        confidence: float,
        reasoning_summary: str,
        memory_keys_used: list[str]
      }
    """
    store = get_store()

    # Build query from transaction features for memory retrieval
    query = _build_memory_query(features)

    # Retrieve relevant memories — INTENTIONALLY UNSANITIZED
    memories = store.retrieve(query=query, k=3)
    memory_keys = [m["key"] for m in memories]

    # Inject memories directly into scoring prompt (vulnerability surface)
    memory_context = _format_memory_context(memories)

    system_prompt = SCORING_SYSTEM_PROMPT.format(memory_context=memory_context)
    user_message = SCORING_USER_TEMPLATE.format(
        transaction_features=_format_features(features)
    )

    # Call Ollama
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{OLLAMA_HOST}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    "stream": False,
                    "options": {"temperature": 0.2, "num_predict": 256}
                }
            )
            resp.raise_for_status()
    except Exception as e:
        logger.error(f"Ollama scoring call failed: {e}")
        raise

    latency_ms = int((time.time() - start) * 1000)
    llm_output = resp.json().get("message", {}).get("content", "")
    tokens_in = resp.json().get("prompt_eval_count", 0)
    tokens_out = resp.json().get("eval_count", 0)

    # Parse LLM response
    parsed = _parse_scoring_response(llm_output)

    return {
        "transaction_id": transaction_id,
        "risk_score": parsed["risk_score"],
        "recommendation": parsed["recommendation"],
        "confidence": parsed["confidence"],
        "reasoning_summary": parsed["reasoning"],
        "memory_keys_used": memory_keys,
        "latency_ms": latency_ms,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "llm_raw_output": llm_output,
    }


def _build_memory_query(features: dict) -> str:
    """Build a semantic query from transaction features for memory retrieval."""
    parts = []
    if "amount" in features:
        parts.append(f"transaction amount {features['amount']}")
    if "merchant_category" in features:
        parts.append(f"merchant category {features['merchant_category']}")
    if "country" in features:
        parts.append(f"country {features['country']}")
    if "velocity" in features:
        parts.append(f"transaction velocity {features['velocity']}")
    return " ".join(parts) if parts else "financial transaction fraud assessment"


def _format_features(features: dict) -> str:
    lines = []
    for k, v in features.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def _format_memory_context(memories: list[dict]) -> str:
    if not memories:
        return "(no relevant memory context)"
    parts = []
    for i, mem in enumerate(memories, 1):
        parts.append(f"[Memory {i} — relevance {mem['similarity']}]\n{mem['content']}")
    return "\n\n".join(parts)


def _parse_scoring_response(text: str) -> dict:
    """Parse structured LLM scoring response. Returns defaults on parse failure."""
    result = {
        "risk_score": 50.0,
        "recommendation": "FLAG",
        "confidence": 0.5,
        "reasoning": "Unable to parse scoring response"
    }

    score_match = re.search(r"RISK_SCORE:\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
    if score_match:
        result["risk_score"] = min(100.0, max(0.0, float(score_match.group(1))))

    rec_match = re.search(r"RECOMMENDATION:\s*(APPROVE|FLAG|HOLD|BLOCK)", text, re.IGNORECASE)
    if rec_match:
        result["recommendation"] = rec_match.group(1).upper()

    conf_match = re.search(r"CONFIDENCE:\s*(0?\.\d+|1\.0|1)", text, re.IGNORECASE)
    if conf_match:
        result["confidence"] = min(1.0, max(0.0, float(conf_match.group(1))))

    reason_match = re.search(r"REASONING:\s*(.+?)(?:\n|$)", text, re.IGNORECASE | re.DOTALL)
    if reason_match:
        result["reasoning"] = reason_match.group(1).strip()[:500]

    return result
