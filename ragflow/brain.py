"""RAGFlow brain — orchestrates retrieval and Gemini generation."""

from __future__ import annotations

import logging

from google import genai

from ragflow.store import VectorStore

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are RAGFlow, a helpful document-question-answering assistant.

INSTRUCTIONS:
• Answer the user's question using ONLY the provided context excerpts below.
• Cite page numbers in your answer (e.g. "According to page 3, …").
• If the context does not contain enough information to answer, say:
  "I don't have enough information in the uploaded documents to answer that."
• Be concise, accurate, and professional.
• Do NOT make up facts that are not in the context.
"""


class RAGFlowBrain:
    """Orchestrates retrieval from the vector store and answer generation via Gemini.

    Usage::

        brain = RAGFlowBrain(vector_store)
        result = brain.ask("What is the main finding?", api_key="...")
    """

    def __init__(self, vector_store: VectorStore) -> None:
        """Initialise with a ready-to-use :class:`VectorStore`.

        Args:
            vector_store: The vector store used for chunk retrieval.
        """
        self._store = vector_store

    def ask(
        self,
        query: str,
        api_key: str,
        conversation_history: list | None = None,
    ) -> dict:
        """Answer a user query using RAG.

        Args:
            query: The user's natural-language question.
            api_key: Google AI API key.
            conversation_history: Optional list of prior
                ``{"role": ..., "content": ...}`` messages for multi-turn context.

        Returns:
            A dict with:
                - answer (str): The generated answer text.
                - sources (list[dict]): Retrieved chunks used as context,
                  each with keys text, page, score, doc_name.
        """
        # 1. Retrieve relevant chunks.
        sources = self._store.search(query, api_key, top_k=5)

        # 2. Build the prompt.
        context_block = self._format_context(sources)
        history_block = self._format_history(conversation_history)

        prompt = (
            f"{_SYSTEM_PROMPT}\n\n"
            f"=== RETRIEVED CONTEXT ===\n{context_block}\n\n"
        )
        if history_block:
            prompt += f"=== CONVERSATION HISTORY ===\n{history_block}\n\n"
        prompt += f"=== USER QUESTION ===\n{query}"

        # 3. Generate answer with retry for rate limits.
        client = genai.Client(api_key=api_key)
        answer = self._generate_with_retry(client, prompt)

        return {"answer": answer, "sources": sources}

    def _generate_with_retry(self, client, prompt: str, max_retries: int = 3) -> str:
        """Call Gemini with exponential backoff on rate limit errors."""
        import time
        for attempt in range(1, max_retries + 1):
            try:
                response = client.models.generate_content(
                    model="gemini-3.1-flash-lite",
                    contents=prompt,
                )
                return response.text or "I was unable to generate an answer."
            except Exception as exc:
                if "429" in str(exc) and attempt < max_retries:
                    wait = 2 ** attempt
                    logger.warning("Rate limited (attempt %d/%d), retrying in %ds", attempt, max_retries, wait)
                    time.sleep(wait)
                else:
                    raise

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_context(sources: list[dict]) -> str:
        """Format retrieved chunks into a numbered context block."""
        if not sources:
            return "(No relevant context found in uploaded documents.)"
        lines: list[str] = []
        for i, src in enumerate(sources, 1):
            lines.append(
                f"[{i}] (Document: {src['doc_name']}, Page {src['page']}, "
                f"Relevance: {src['score']:.2f})\n{src['text']}"
            )
        return "\n\n".join(lines)

    @staticmethod
    def _format_history(history: list | None) -> str:
        """Format conversation history into a readable block."""
        if not history:
            return ""
        lines: list[str] = []
        for msg in history:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)
