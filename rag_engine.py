import json
import os
import sys
from typing import List, Dict, Any

from chunksmith.config import load_settings
from chunksmith.llm_support.client import llm_completion, extract_json
from chunksmith.llm_support.prompts import build_node_selection_prompt, build_rag_answer_prompt

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

from chunksmith.llm_support.prompts import NODE_SELECTION_SYSTEM

def select_relevant_nodes(settings, tree_toon: str, query: str) -> List[str]:
    """Ask LLM to select relevant node IDs from the summary tree."""
    system_msg = {"role": "system", "content": NODE_SELECTION_SYSTEM}
    user_prompt = f"DOCUMENT TREE (TOON format):\n{tree_toon}\n\nUSER QUERY: {query}\n\nReturn the JSON list of relevant node IDs:"
    
    response = llm_completion(settings, settings.rag_model, user_prompt, chat_history=[system_msg])
    node_ids = extract_json(response)
    if isinstance(node_ids, list):
        return [str(nid) for nid in node_ids]
    return []

def generate_final_answer(settings, context_texts: List[str], query: str) -> str:
    """Generate final answer using the extracted context."""
    context = "\n\n---\n\n".join(context_texts)
    prompt = build_rag_answer_prompt(query, context)
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
