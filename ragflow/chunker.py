"""Sentence-aware document chunking with overlap."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Chunk:
    """A single chunk of document text with provenance metadata.

    Attributes:
        text: The chunk's textual content.
        page_num: The 1-based source page number.
        chunk_id: Sequential chunk index within the document.
        doc_name: Name of the source document.
    """

    text: str
    page_num: int
    chunk_id: int
    doc_name: str


# Pre-compiled patterns for splitting.
_PARAGRAPH_RE = re.compile(r"\n{2,}")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> list[str]:
    """Split *text* into sentence-level fragments."""
    return [s for s in _SENTENCE_RE.split(text) if s.strip()]


def _hard_split(text: str, size: int) -> list[str]:
    """Last-resort character-level split."""
    return [text[i : i + size] for i in range(0, len(text), size)]


def chunk_document(
    pages: list[dict],
    doc_name: str,
    chunk_size: int = 800,
    overlap: int = 100,
) -> list[Chunk]:
    """Split extracted pages into overlapping chunks.

    The algorithm tries three granularity levels in order:
    1. Paragraph boundaries (double newlines).
    2. Sentence boundaries (punctuation followed by whitespace).
    3. Hard character-count split as a final fallback.

    Args:
        pages: Output of :func:`pdf_reader.extract_pages`.
        doc_name: Human-readable document name used for metadata.
        chunk_size: Target maximum characters per chunk.
        overlap: Number of characters to repeat between consecutive chunks
                 for context continuity.

    Returns:
        An ordered list of :class:`Chunk` objects.
    """
    # Build a flat list of (fragment_text, page_num) tuples.
    fragments: list[tuple[str, int]] = []
    for page in pages:
        text = page["text"]
        page_num = page["page_num"]
        if not text:
            continue
        # Split on paragraph boundaries first.
        paragraphs = _PARAGRAPH_RE.split(text)
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            # If the paragraph fits in one chunk, keep it whole.
            if len(para) <= chunk_size:
                fragments.append((para, page_num))
            else:
                # Try sentence splitting.
                sentences = _split_sentences(para)
                if len(sentences) > 1:
                    for sent in sentences:
                        sent = sent.strip()
                        if sent:
                            fragments.append((sent, page_num))
                else:
                    # Hard character split as last resort.
                    for piece in _hard_split(para, chunk_size):
                        fragments.append((piece, page_num))

    if not fragments:
        return []

    # Merge fragments into chunks of approximately *chunk_size* characters.
    chunks: list[Chunk] = []
    current_text = ""
    current_page = fragments[0][1]
    chunk_id = 0

    for frag_text, frag_page in fragments:
        candidate = f"{current_text} {frag_text}".strip() if current_text else frag_text
        if len(candidate) <= chunk_size:
            current_text = candidate
            current_page = frag_page  # track latest page
        else:
            # Emit the current chunk.
            if current_text:
                chunks.append(Chunk(
                    text=current_text,
                    page_num=current_page,
                    chunk_id=chunk_id,
                    doc_name=doc_name,
                ))
                chunk_id += 1

            # Start next chunk with overlap from the tail of the previous one.
            if overlap and current_text:
                overlap_text = current_text[-overlap:]
                current_text = f"{overlap_text} {frag_text}".strip()
            else:
                current_text = frag_text
            current_page = frag_page

    # Don't forget the last accumulated chunk.
    if current_text.strip():
        chunks.append(Chunk(
            text=current_text.strip(),
            page_num=current_page,
            chunk_id=chunk_id,
            doc_name=doc_name,
        ))

    return chunks
