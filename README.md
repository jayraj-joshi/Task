# ChunkSmith PageIndexer

Standalone toolset: **read PDF → tag pages → LLM outline → nested tree → Hierarchical RAG**.

## Layout

- `api.py` — **NEW:** FastAPI server with Neon DB integration.
- `chunksmith/` — Core modules (config, parser, LLM support, tree building).
- `interface/` — CLI logic and display utilities.
- `rag_engine.py` — Interactive hierarchical RAG system (CLI version).
- `generate_trees.py` — Utility to convert extracted JSON to TOON summary trees.
- `verify_rag.py` — Verification script for the RAG pipeline.

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configuration
Copy `.env.example` to `.env` and configure your keys:

```env
HF_TOKEN=your_huggingface_token

# Model for initial PDF processing (Qwen suggested)
PAGEINDEX_MODEL=Qwen/Qwen2.5-7B-Instruct:together

# Model for RAG steps (Phi-4-mini suggested)
RAG_MODEL=microsoft/Phi-4-mini-instruct:featherless-ai

# Database for API storage
NEONDB_STRING='postgresql://user:pass@host/dbname?sslmode=require'
```

---

## Deployment (FastAPI + Database)

The system now includes a production-ready API that uses a database to cache processed documents.

### Start the API Server
```bash
python api.py
```
Visit `http://localhost:8000/docs` for the interactive API documentation.

### API Features
- **Smart Caching:** Files are hashed using SHA-256. If you upload a PDF that has already been processed, the API returns the cached result instantly from the DB, saving LLM costs.
- **Persistence:** All document trees and summaries are stored in PostgreSQL (Neon), allowing you to query them by `document_id` anytime.
- **Endpoints:**
  - `POST /process`: Upload a PDF to index it. (Add `?force=true` to re-process an existing file).
  - `POST /query`: Query a processed document by its ID.
  - `GET /documents`: List all indexed documents.

---

## CLI Usage (Local Files)

If you prefer using local `.json` and `.toon` files instead of a database:

### 1. Extract Outline from PDF
Run the extraction script to build the document structure.
```bash
python3 examples/process_book.py path/to/your_file.pdf -o output.json --summary
```

### 2. Generate Summary Trees
Convert the full `output.json` into a lightweight hierarchical summary tree (`tree.toon`).
```bash
python3 generate_trees.py
```

### 3. Run Hierarchical RAG
Start an interactive CLI session to chat with the document.
```bash
python3 rag_engine.py
```

---

## How the Hierarchical RAG Works

1.  **Selection**: The user query and the summary tree (TOON format) are sent to the LLM to identify the most relevant sections (node IDs).
2.  **Extraction**: The full text for only those selected sections is retrieved from the DB/JSON.
3.  **Generation**: The extracted context and query are sent to the LLM for the final answer.

This approach **minimizes token usage** and **avoids vector database complexity** by using the document's natural hierarchy as the index.

## Development

- **`verify_rag.py`**: Run this to test the full pipeline with a pre-defined query.
- **`chunksmith/llm_support/client.py`**: Handles API calls to Hugging Face / OpenAI.
- **`api.py`**: Uses SQLAlchemy to manage the PostgreSQL schema.
# Task
