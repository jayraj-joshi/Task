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
## API Reference

The API is the primary way to interact with the PageIndexer in a production environment. 

### 1. List Documents
Retrieve a list of all documents that have been processed and stored in the database.

**Endpoint:** `GET /documents`

**cURL Example:**
```bash
curl -X GET http://localhost:8000/documents
```

**Response Schema:**
```json
[
  {
    "id": 1,
    "filename": "annual_report.pdf",
    "created_at": "2024-03-20T10:00:00Z"
  }
]
```

---

### 2. Process Document
Upload a PDF to be parsed and indexed. This performs the hierarchical summary extraction.

**Endpoint:** `POST /process`

**Parameters:**
- `file`: The PDF file (form-data).
- `force` (optional): If `true`, re-processes the file even if it has been indexed before.

**cURL Example:**
```bash
curl -X POST http://localhost:8000/process \
  -F "file=@/path/to/document.pdf"
```

**cURL Example (Force Re-process):**
```bash
curl -X POST "http://localhost:8000/process?force=true" \
  -F "file=@/path/to/document.pdf"
```

**Response Schema:**
```json
{
  "message": "Document processed successfully",
  "document_id": 1,
  "filename": "document.pdf"
}
```

---

### 3. Query Document
Ask a question against a specific processed document using the Hierarchical RAG pipeline.

**Endpoint:** `POST /query`

**Request Schema:**
```json
{
  "document_id": 1,
  "query": "What are the key financial highlights?"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"document_id": 1, "query": "What are the key financial highlights?"}'
```

**Response Schema:**
```json
{
  "answer": "The key highlights include a 15% increase in revenue...",
  "selected_nodes": ["0001", "0005", "0012"]
}
```

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
