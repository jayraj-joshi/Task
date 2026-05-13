
import os
from sqlalchemy import create_engine, Column, Integer, String, Text, JSON, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import json

load_dotenv()

DATABASE_URL = os.getenv("NEONDB_STRING")
if DATABASE_URL:
    DATABASE_URL = DATABASE_URL.strip("'")

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

def fetch_data():
    db = SessionLocal()
    try:
        docs = db.query(ProcessedDocument).all()
        for doc in docs:
            print(f"Found doc: {doc.filename}")
            # Save JSON
            json_filename = f"{doc.filename.replace('.pdf', '')}_output.json"
            with open(json_filename, "w") as f:
                json.dump(doc.json_data, f, indent=2)
            
            # Save TOON
            toon_filename = f"{doc.filename.replace('.pdf', '')}_output.toon"
            with open(toon_filename, "w") as f:
                f.write(doc.toon_data)
            
            print(f"Saved {json_filename} and {toon_filename}")
    finally:
        db.close()

if __name__ == "__main__":
    fetch_data()
