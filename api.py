import hashlib
import os
import json
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, JSON, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

from chunksmith import build_outline_from_pdf, load_settings, toon
from rag_engine import select_relevant_nodes, find_node_text, generate_final_answer

# Load environment variables
load_dotenv()

# Database Setup
DATABASE_URL = os.getenv("NEONDB_STRING")
if DATABASE_URL:
    DATABASE_URL = DATABASE_URL.strip("'")
if not DATABASE_URL:
    raise ValueError("NEONDB_STRING not found in environment variables")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ProcessedDocument(Base):
    __tablename__ = "processed_documents"

    id = Column(Integer, primary_key=True, index=True)
    file_hash = Column(String, unique=True, index=True)
    filename = Column(String)
    json_data = Column(JSON)
    toon_data = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI App
app = FastAPI(title="ChunkSmith PageIndexer API")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic Models
class QueryRequest(BaseModel):
    document_id: int
    query: str

class QueryResponse(BaseModel):
    answer: str
    selected_nodes: List[str]

def calculate_file_hash(file_content: bytes) -> str:
    return hashlib.sha256(file_content).hexdigest()

@app.post("/process", response_model=dict)
async def process_pdf(
    file: UploadFile = File(...), 
    force: bool = False, 
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content = await file.read()
    file_hash = calculate_file_hash(content)

    # Check if already processed
    existing_doc = db.query(ProcessedDocument).filter(ProcessedDocument.file_hash == file_hash).first()
    
    if existing_doc and not force:
        return {
            "message": "Document already processed (use force=true to re-process)",
            "document_id": existing_doc.id,
            "filename": existing_doc.filename
        }
    
    # If forcing, delete the old record first to avoid unique constraint issues
    if existing_doc and force:
        db.delete(existing_doc)
        db.commit()

    # Save temp file for processing
    temp_path = Path(f"temp_{file_hash}.pdf")
    with open(temp_path, "wb") as f:
        f.write(content)

    try:
        print(f"[*] Processing new PDF: {file.filename}")
        settings = load_settings()
        
        # Build outline
        result = build_outline_from_pdf(
            temp_path,
            settings,
            add_text=True,
            assign_node_ids=True,
            add_summary=True,
            add_word_range=True,
            generate_doc_summary=True
        )

        # Generate TOON data (stripping text for the tree view)
        def _strip_text(obj):
            if isinstance(obj, dict):
                return {k: _strip_text(v) for k, v in obj.items() if k != "text"}
            if isinstance(obj, list):
                return [_strip_text(x) for x in obj]
            return obj

        toon_data = toon.encode(_strip_text(result))

        # Save to DB
        new_doc = ProcessedDocument(
            file_hash=file_hash,
            filename=file.filename,
            json_data=result,
            toon_data=toon_data
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)

        return {
            "message": "Document processed successfully",
            "document_id": new_doc.id,
            "filename": new_doc.filename
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_path.exists():
            os.remove(temp_path)

@app.post("/query", response_model=QueryResponse)
async def query_document(request: QueryRequest, db: Session = Depends(get_db)):
    doc = db.query(ProcessedDocument).filter(ProcessedDocument.id == request.document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    settings = load_settings()
    
    try:
        # Step 1: Select relevant nodes
        node_ids = select_relevant_nodes(settings, doc.toon_data, request.query)
        
        if not node_ids:
            return QueryResponse(answer="No relevant sections found in the document.", selected_nodes=[])

        # Step 2: Extract context from JSON data
        context_texts = find_node_text(doc.json_data.get("structure", []), node_ids)
        
        if not context_texts:
            return QueryResponse(answer="Could not retrieve text for the selected sections.", selected_nodes=node_ids)

        # Step 3: Generate answer
        answer = generate_final_answer(settings, context_texts, request.query)

        return QueryResponse(
            answer=answer,
            selected_nodes=node_ids
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents")
async def list_documents(db: Session = Depends(get_db)):
    docs = db.query(ProcessedDocument.id, ProcessedDocument.filename, ProcessedDocument.created_at).all()
    return [{"id": d.id, "filename": d.filename, "created_at": d.created_at} for d in docs]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
