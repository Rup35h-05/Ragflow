"""Text embedding via Google Gemini text-embedding-004 model."""

from __future__ import annotations

import time
import logging

from google import genai

logger = logging.getLogger(__name__)

_BATCH_SIZE = 100
_MAX_RETRIES = 3
_BASE_BACKOFF = 1.0  # seconds


def embed_texts(texts: list[str], api_key: str) -> list[list[float]]:
    """Embed a list of texts using Gemini text-embedding-004.

    Texts are batched in groups of 100 to stay within API limits.
    Each batch is retried up to 3 times with exponential backoff on
    transient failures.

    Args:
        texts: Strings to embed.
        api_key: Google AI API key.

    Returns:
        A list of embedding vectors (each a list of floats), one per
        input text, preserving order.

    Raises:
        RuntimeError: If embedding fails after all retries.
    """
    client = genai.Client(api_key=api_key)
    all_embeddings: list[list[float]] = []

    for batch_start in range(0, len(texts), _BATCH_SIZE):
        batch = texts[batch_start : batch_start + _BATCH_SIZE]
        last_error: Exception | None = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                result = client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=batch,
                )
                all_embeddings.extend(e.values for e in result.embeddings)
                break
            except Exception as exc:
                last_error = exc
                if attempt < _MAX_RETRIES:
                    wait = _BASE_BACKOFF * (2 ** (attempt - 1))
                    logger.warning(
                        "Embedding batch %d–%d failed (attempt %d/%d), "
                        "retrying in %.1fs: %s",
                        batch_start,
                        batch_start + len(batch) - 1,
                        attempt,
                        _MAX_RETRIES,
                        wait,
                        exc,
                    )
                    time.sleep(wait)
        else:
            raise RuntimeError(
                f"Embedding failed after {_MAX_RETRIES} retries: {last_error}"
            ) from last_error

    return all_embeddings
