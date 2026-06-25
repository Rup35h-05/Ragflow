# RAGFlow 🔄📄

**RAG-Powered Document Intelligence** — Upload PDFs, ask questions, get answers with source citations.

RAGFlow is a fully featured Retrieval-Augmented Generation chatbot that lets you have intelligent conversations with your documents. Built with Google's Gemini API for state-of-the-art language understanding and ChromaDB for efficient local vector search.

---

## Features

- **📄 PDF Upload & Processing** — Drag-and-drop PDF upload with intelligent page-aware text chunking
- **🧠 Gemini-Powered RAG** — Uses Gemini 3.1 Flash-Lite for generation and gemini-embedding-001 for semantic search
- **📍 Source Citations** — Every answer shows exactly which pages and passages were used
- **💾 Local Vector Store** — ChromaDB runs locally, no external database accounts needed
- **📚 Multi-Document Support** — Upload and query across multiple documents
- **💬 Conversation Memory** — Multi-turn conversations with context awareness
- **🎨 Modern Chat UI** — Dark glassmorphism design with smooth animations
- **🚀 Deploy-Ready** — Docker + Gunicorn configuration included

---

## Quick Start

### 1. Clone & Install

```bash
git clone <your-repo-url>
cd ragflow

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Get a Gemini API Key

Get your free API key from [Google AI Studio](https://aistudio.google.com/apikey).

### 3. Run

```bash
python server.py
```

Open **http://localhost:5001** in your browser.

### 4. Use

1. Enter your Gemini API key in the sidebar
2. Upload a PDF document
3. Start asking questions!

---

## Architecture

```
ragflow/
├── server.py              # Flask API server
├── ragflow/               # Core RAG engine
│   ├── pdf_reader.py      # PDF text extraction with page tracking
│   ├── chunker.py         # Sentence-aware text chunking with overlap
│   ├── embeddings.py      # Gemini embedding wrapper with retry logic
│   ├── store.py           # ChromaDB vector store manager
│   └── brain.py           # RAG orchestrator (retrieval + generation)
├── static/                # Frontend SPA
│   ├── index.html         # Chat interface
│   ├── styles.css         # Dark glassmorphism theme
│   └── app.js             # Client-side logic
├── Dockerfile             # Production deployment
└── requirements.txt       # Python dependencies
```

### How RAG Works in RAGFlow

```
User Question
      │
      ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Embed      │────▶│  ChromaDB    │────▶│  Top-K      │
│   Query      │     │  Search      │     │  Chunks     │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                 │
                                                 ▼
                                        ┌─────────────┐
                                        │   Gemini     │
                                        │   + Context  │
                                        │   + History  │
                                        └──────┬──────┘
                                                │
                                                ▼
                                        ┌─────────────┐
                                        │   Answer +   │
                                        │   Sources    │
                                        └─────────────┘
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| LLM | Google Gemini 3.1 Flash-Lite |
| Embeddings | Gemini gemini-embedding-001 |
| Vector Store | ChromaDB (local) |
| PDF Parsing | PyMuPDF |
| Backend | Flask |
| Frontend | Vanilla HTML/CSS/JS |
| Production | Gunicorn + Docker |

---

## Docker Deployment

```bash
docker build -t ragflow .
docker run -p 5001:5001 ragflow
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serve the web UI |
| `/api/upload` | POST | Upload and process a PDF |
| `/api/chat` | POST | Send a question, get an answer with sources |
| `/api/documents` | GET | List all indexed documents |
| `/api/documents/<name>` | DELETE | Remove a document |

---

## License

MIT License — feel free to use, modify, and distribute.
