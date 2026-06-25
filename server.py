"""Flask server for the RAGFlow document chatbot."""

from __future__ import annotations

import os
import logging

from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from ragflow.pdf_reader import extract_pages
from ragflow.chunker import chunk_document
from ragflow.store import VectorStore
from ragflow.brain import RAGFlowBrain

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# App & shared instances
# ---------------------------------------------------------------------------

app = Flask(__name__, static_folder=STATIC_DIR)
CORS(app)

vector_store = VectorStore()
brain = RAGFlowBrain(vector_store)


def _get_api_key(from_json: dict | None = None) -> str:
    """Resolve the API key from the request payload or environment.

    Priority: request payload → environment variable.

    Raises:
        ValueError: If no API key can be resolved.
    """
    key = None
    if from_json and isinstance(from_json, dict):
        key = from_json.get("api_key")
    if not key:
        key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("Missing API key. Provide 'api_key' in the request or set GEMINI_API_KEY env var.")
    return key


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Serve the frontend SPA."""
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/api/upload", methods=["POST"])
def upload_document():
    """Upload and index a PDF document.

    Expects multipart/form-data with:
        - file: the PDF file
        - api_key: (optional) form field
    """
    try:
        # --- file ---
        if "file" not in request.files:
            return jsonify({"success": False, "message": "No file provided."}), 400
        file = request.files["file"]
        if not file.filename:
            return jsonify({"success": False, "message": "Empty filename."}), 400
        if not file.filename.lower().endswith(".pdf"):
            return jsonify({"success": False, "message": "Only PDF files are supported."}), 400

        # --- api key ---
        api_key_data: dict = {}
        if request.form.get("api_key"):
            api_key_data["api_key"] = request.form["api_key"]
        try:
            api_key = _get_api_key(api_key_data)
        except ValueError as exc:
            return jsonify({"success": False, "message": str(exc)}), 400

        # --- save file ---
        doc_name = file.filename
        save_path = os.path.join(UPLOAD_DIR, doc_name)
        file.save(save_path)
        logger.info("Saved upload to %s", save_path)

        # --- process ---
        pages = extract_pages(save_path)
        chunks = chunk_document(pages, doc_name)
        vector_store.add_document(doc_name, chunks, api_key)

        return jsonify({
            "success": True,
            "document_name": doc_name,
            "chunks_count": len(chunks),
            "message": f"Document '{doc_name}' uploaded and indexed ({len(chunks)} chunks).",
        })

    except Exception as exc:
        logger.exception("Upload failed")
        return jsonify({"success": False, "message": f"Upload failed: {exc}"}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    """Answer a question using RAG over uploaded documents."""
    try:
        data = request.get_json(silent=True) or {}
        query = data.get("query", "").strip()
        if not query:
            return jsonify({"answer": "", "sources": [], "message": "Empty query."}), 400

        try:
            api_key = _get_api_key(data)
        except ValueError as exc:
            return jsonify({"answer": "", "sources": [], "message": str(exc)}), 400

        conversation_history = data.get("conversation_history")
        result = brain.ask(query, api_key, conversation_history=conversation_history)

        return jsonify({
            "answer": result["answer"],
            "sources": result["sources"],
        })

    except Exception as exc:
        logger.exception("Chat failed")
        return jsonify({"answer": "", "sources": [], "message": f"Chat error: {exc}"}), 500


@app.route("/api/documents", methods=["GET"])
def list_documents():
    """List all indexed documents with chunk counts."""
    try:
        docs = vector_store.list_documents()
        return jsonify({"documents": docs})
    except Exception as exc:
        logger.exception("Failed to list documents")
        return jsonify({"documents": [], "message": f"Error: {exc}"}), 500


@app.route("/api/documents/<name>", methods=["DELETE"])
def delete_document(name: str):
    """Delete all indexed chunks for a document."""
    try:
        vector_store.delete_document(name)
        return jsonify({"success": True, "message": f"Document '{name}' deleted."})
    except Exception as exc:
        logger.exception("Failed to delete document '%s'", name)
        return jsonify({"success": False, "message": f"Delete failed: {exc}"}), 500


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
