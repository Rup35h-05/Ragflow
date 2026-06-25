"""ChromaDB-backed vector store for RAGFlow documents."""

from __future__ import annotations

import os
import logging
from typing import Any

import chromadb

from ragflow.chunker import Chunk
from ragflow.embeddings import embed_texts

logger = logging.getLogger(__name__)

_CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_data")
_COLLECTION_NAME = "ragflow_docs"


class VectorStore:
    """Persistent vector store wrapping ChromaDB.

    All document chunks are stored in a single collection with metadata
    tracking the source document name, page number, and chunk ID.
    """

    def __init__(self) -> None:
        """Initialise the ChromaDB persistent client and get/create the collection."""
        os.makedirs(_CHROMA_DIR, exist_ok=True)
        self._client = chromadb.PersistentClient(path=_CHROMA_DIR)
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("VectorStore initialised (dir=%s, collection=%s)", _CHROMA_DIR, _COLLECTION_NAME)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_document(self, doc_name: str, chunks: list[Chunk], api_key: str) -> None:
        """Embed and store document chunks.

        Args:
            doc_name: Logical document name (used for filtering & IDs).
            chunks: Pre-chunked text with metadata.
            api_key: Google AI API key forwarded to the embedding function.
        """
        if not chunks:
            logger.warning("add_document called with empty chunk list for '%s'", doc_name)
            return

        texts = [c.text for c in chunks]
        embeddings = embed_texts(texts, api_key)

        ids = [f"{doc_name}_{c.chunk_id}" for c in chunks]
        metadatas = [
            {
                "text": c.text,
                "page_num": c.page_num,
                "doc_name": c.doc_name,
                "chunk_id": c.chunk_id,
            }
            for c in chunks
        ]

        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        logger.info("Stored %d chunks for document '%s'", len(chunks), doc_name)

    def search(self, query: str, api_key: str, top_k: int = 5) -> list[dict]:
        """Retrieve the most relevant chunks for a query.

        Args:
            query: User query string.
            api_key: Google AI API key.
            top_k: Maximum number of results to return.

        Returns:
            A list of dicts with keys: text, page, score, doc_name.
            Results are sorted best-match-first.
        """
        if self._collection.count() == 0:
            return []

        query_embedding = embed_texts([query], api_key)[0]

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self._collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        hits: list[dict] = []
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc_text, meta, distance in zip(documents, metadatas, distances):
            # ChromaDB cosine distance is in [0, 2]; convert to similarity score.
            score = 1.0 - (distance / 2.0)
            hits.append({
                "text": meta.get("text", doc_text),
                "page": meta.get("page_num", 0),
                "score": round(score, 4),
                "doc_name": meta.get("doc_name", ""),
            })

        return hits

    def delete_document(self, doc_name: str) -> None:
        """Remove all chunks belonging to a document.

        Args:
            doc_name: The document name whose chunks should be deleted.
        """
        # Fetch IDs that match the document name via metadata filter.
        results = self._collection.get(
            where={"doc_name": doc_name},
            include=[],
        )
        ids_to_delete = results.get("ids", [])
        if ids_to_delete:
            self._collection.delete(ids=ids_to_delete)
            logger.info("Deleted %d chunks for document '%s'", len(ids_to_delete), doc_name)
        else:
            logger.warning("No chunks found for document '%s'", doc_name)

    def list_documents(self) -> list[dict]:
        """Return unique document names with their chunk counts.

        Returns:
            A list of dicts: [{name: str, chunks_count: int}, ...].
        """
        all_meta = self._collection.get(include=["metadatas"])
        metadatas = all_meta.get("metadatas", [])

        doc_counts: dict[str, int] = {}
        for meta in metadatas:
            name = meta.get("doc_name", "unknown")
            doc_counts[name] = doc_counts.get(name, 0) + 1

        return [
            {"name": name, "chunks_count": count}
            for name, count in sorted(doc_counts.items())
        ]
