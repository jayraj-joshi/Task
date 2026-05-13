import json
import os
import sys

from rag_engine import select_relevant_nodes, find_node_text, generate_final_answer
from chunksmith.config import load_settings

def run_verification():
    print("--- RAG VERIFICATION (Round 2) ---")
    settings = load_settings()
    
    with open("output.toon", "r") as f:
        tree_toon = f.read()
    
    with open("output.json", "r") as f:
        full_doc = json.load(f)

    query = "How have the risks to achieving the Committee's employment and inflation goals changed according to the March 2024 Summary?"
    print(f"Query: {query}")
    
    print("\nStep 1: Selecting nodes...")
    node_ids = select_relevant_nodes(settings, tree_toon, query)
    print(f"Selected Nodes: {node_ids}")
    
    print("\nStep 2: Extracting context...")
    context_texts = find_node_text(full_doc.get("structure", []), node_ids)
    
    print("\nStep 3: Generating answer...")
    # These functions already use settings.rag_model inside rag_engine.py
    answer = generate_final_answer(settings, context_texts, query)
    
    print("\n--- RESULT ---")
    print(answer)
    print("--------------")
    
    # Expected: "moving into better balance"
    if "better balance" in answer.lower():
        print("\nVERIFICATION: SUCCESS (Answer correctly identifies the 'better balance' trend)")
    else:
        print("\nVERIFICATION: FAILED (Could not find expected information)")

if __name__ == "__main__":
    run_verification()
