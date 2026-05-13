import json
import os
import sys
from typing import List, Dict, Any

from chunksmith.config import load_settings
from chunksmith.llm_support.client import llm_completion, extract_json

def find_node_text(nodes: List[Dict[str, Any]], node_ids: List[str]) -> List[str]:
    """Recursively find text for given node IDs in the document structure."""
    texts = []
    for node in nodes:
        if node.get("node_id") in node_ids:
            if "text" in node:
                texts.append(node["text"])
            else:
                # If the node itself doesn't have text (maybe it's a structural parent),
                # we might want to collect all its children's text? 
                # For now, let's just collect the text field if it exists.
                pass
        
        if "nodes" in node and node["nodes"]:
            texts.extend(find_node_text(node["nodes"], node_ids))
    return texts

def select_relevant_nodes(settings, tree_toon: str, query: str) -> List[str]:
    """Ask LLM to select relevant node IDs from the summary tree."""
    prompt = f"""
You are a precision retrieval assistant. Below is a hierarchical summary (in TOON format) of a document.
Your task is to identify which sections (node IDs) are most relevant to answer the user's query.

DOCUMENT TREE:
{tree_toon}

USER QUERY: {query}

Instructions:
1. Analyze the query and the summaries in the tree.
2. Return a JSON list of node IDs (strings) that likely contain the information needed to answer the query.
3. Be specific. If sub-sections are available, select the most relevant sub-sections.
4. Return ONLY the JSON list of strings.

Example Output:
["0003", "0009"]
"""
    response = llm_completion(settings, settings.rag_model, prompt)
    node_ids = extract_json(response)
    if isinstance(node_ids, list):
        return [str(nid) for nid in node_ids]
    return []

def generate_final_answer(settings, context_texts: List[str], query: str) -> str:
    """Generate final answer using the extracted context."""
    context = "\n\n---\n\n".join(context_texts)
    prompt = f"""
You are an expert document assistant. Use the provided context from the document to answer the user's query.

CONTEXT:
{context}

USER QUERY: {query}

Instructions:
- Answer the query accurately based ONLY on the provided context.
- If the context doesn't contain the answer, explicitly state that the information is not available in the selected sections.
- Use a professional and helpful tone.
- If relevant, mention which parts of the context you are using.
"""
    return llm_completion(settings, settings.rag_model, prompt, max_tokens=2048)

def main():
    print("Initializing RAG Engine...")
    settings = load_settings()
    
    # Load the summary tree (TOON)
    try:
        with open("tree.toon", "r") as f:
            tree_toon = f.read()
    except FileNotFoundError:
        print("Error: tree.toon not found. Run generate_trees.py first.")
        return

    # Load the full document data
    try:
        with open("output.json", "r") as f:
            full_doc = json.load(f)
    except FileNotFoundError:
        print("Error: output.json not found.")
        return

    print("RAG Engine Ready!")
    
    while True:
        try:
            query = input("\n[Q]: ")
            if not query.strip():
                continue
            if query.lower() in ["exit", "quit"]:
                break
            
            print(f"[*] Selecting relevant nodes for: '{query}'")
            node_ids = select_relevant_nodes(settings, tree_toon, query)
            print(f"[*] Selected Node IDs: {node_ids}")
            
            if not node_ids:
                print("[!] No relevant nodes found by the LLM.")
                continue
                
            print("[*] Extracting text context...")
            context_texts = find_node_text(full_doc.get("structure", []), node_ids)
            
            if not context_texts:
                print("[!] Could not find text for selected nodes in output.json.")
                continue
                
            print("[*] Generating answer...")
            answer = generate_final_answer(settings, context_texts, query)
            
            print("\n" + "="*50)
            print(f"ANSWER:\n{answer}")
            print("="*50 + "\n")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()
