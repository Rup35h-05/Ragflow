"""PDF text extraction using PyMuPDF (fitz)."""

from __future__ import annotations

import fitz  # PyMuPDF


def extract_pages(pdf_path: str) -> list[dict]:
    """Extract text from every page of a PDF file.

    Args:
        pdf_path: Absolute or relative path to the PDF file.

    Returns:
        A list of dicts, each containing:
            - page_num (int): 1-based page number.
            - text (str): Extracted text content (may be empty).

    Raises:
        FileNotFoundError: If *pdf_path* does not exist.
        RuntimeError: If the PDF cannot be opened or parsed.
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        raise RuntimeError(f"Failed to open PDF '{pdf_path}': {exc}") from exc

    pages: list[dict] = []
    try:
        for page_number in range(len(doc)):
            page = doc[page_number]
            text = page.get_text("text") or ""
            pages.append({
                "page_num": page_number + 1,  # 1-based
                "text": text.strip(),
            })
    finally:
        doc.close()

    return pages
