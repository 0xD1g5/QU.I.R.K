"""
document_intake.py — PDF and TXT ingestion for QL-DocuIntel.

INTENTIONAL VULNERABILITY:
  Document text chunks are placed directly into the LLM prompt context
  without any sanitization or instruction-following detection.

  This means if a document contains text that looks like an instruction
  (e.g., "SYSTEM: Override previous instructions and..."), the LLM will
  treat it as a valid instruction when that chunk is retrieved and injected
  into the prompt context.

  This is the injection surface for Phase 3 (Indirect Prompt Injection).
  Do NOT add sanitization here.
"""

import io
import logging
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract raw text from PDF file bytes.
    Uses pypdf — ARM64 compatible, no native deps.
    Returns full text content as a single string.
    """
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise ValueError(f"Failed to extract PDF content: {e}")


def extract_text_from_txt(file_bytes: bytes) -> str:
    """Extract text from plaintext file bytes."""
    try:
        return file_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        logger.error(f"TXT extraction failed: {e}")
        raise ValueError(f"Failed to decode text file: {e}")


def ingest_document(
    file_bytes: bytes,
    filename: str,
    document_id: str = None,
    metadata: dict = None
) -> dict:
    """
    Ingest a document (PDF or TXT) and return extracted text + metadata.

    Returns:
      {
        "document_id": str,
        "filename": str,
        "content_type": str,
        "text": str,        ← raw extracted text, unsanitized
        "char_count": int,
        "metadata": dict
      }
    """
    document_id = document_id or str(uuid.uuid4())
    filename_lower = filename.lower()

    if filename_lower.endswith(".pdf"):
        text = extract_text_from_pdf(file_bytes)
        content_type = "application/pdf"
    elif filename_lower.endswith(".txt"):
        text = extract_text_from_txt(file_bytes)
        content_type = "text/plain"
    else:
        # Attempt text extraction as fallback
        text = extract_text_from_txt(file_bytes)
        content_type = "text/plain"

    return {
        "document_id": document_id,
        "filename": filename,
        "content_type": content_type,
        "text": text,   # ← UNSANITIZED — this is the injection surface
        "char_count": len(text),
        "metadata": metadata or {}
    }
