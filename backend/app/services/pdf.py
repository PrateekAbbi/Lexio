"""PDF text extraction."""

from __future__ import annotations

import fitz

from app.exceptions import EmptyDocumentError, UnsupportedDocumentError
from app.models import PdfPage


def extract_pdf_text(pdf_bytes: bytes) -> tuple[list[PdfPage], int]:
    """Extract text per page from a PDF byte stream.

    PyMuPDF parsing is CPU-bound and can be slow for larger files, so callers
    should run this function in a worker thread from async request handlers.
    """

    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise UnsupportedDocumentError("Unable to read this PDF file.") from exc

    try:
        pages = [
            PdfPage(page_number=index, text=page.get_text("text").strip())
            for index, page in enumerate(document, start=1)
        ]
        if not any(page.text for page in pages):
            raise EmptyDocumentError("This PDF appears to be scanned. OCR support coming soon.")
        return pages, document.page_count
    finally:
        document.close()

