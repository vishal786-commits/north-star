import logging

import fitz  # PyMuPDF

from app.errors import ExtractionError

logger = logging.getLogger(__name__)

def extract_resume(pdf_bytes: bytes) -> tuple[str, int]:
    """Extract full text and page count from a resume PDF. Sync/blocking
    by design (PyMuPDF is CPU-bound); the endpoint offloads it to a thread."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        logger.exception("Failed to open uploaded file as PDF")
        raise ExtractionError("Could not read the file as a PDF.") from e

    try:
        pages = [page.get_text() for page in doc]
        page_count = len(doc)
    finally:
        doc.close()  # runs even if extraction errors — no leaked handles

    full_text = "\n".join(pages).strip()

    if not full_text:
        # This is the scanned/image-PDF case we flagged earlier.
        raise ExtractionError(
            "No text found. The PDF may be scanned or image-based."
        )

    return full_text, page_count