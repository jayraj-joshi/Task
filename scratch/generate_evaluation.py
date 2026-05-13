
import json
import os
import sys
from typing import List, Dict, Any

# Add current directory to path so we can import from chunksmith
sys.path.append(os.getcwd())

from chunksmith.config import load_settings
from chunksmith.llm_support.client import llm_completion, extract_json
from rag_engine import select_relevant_nodes, generate_final_answer, find_node_text

def generate_evaluation():
    print("Loading document data...")
    with open("alltransformer_output.json", "r") as f:
        full_doc = json.load(f)
    
    with open("alltransformer_output.toon", "r") as f:
        tree_toon = f.read()

    settings = load_settings()
    
    # 1. Generate 10 Queries
    print("Generating 10 queries...")
    query_prompt = f"""
    Based on the following document structure and summary, generate 10 diverse and challenging questions that can be answered using the document.
    
    DOCUMENT SUMMARY:
    {full_doc.get('doc_description', 'N/A')}
    
    STRUCTURE:
    {json.dumps([{'title': n['title'], 'summary': n.get('summary', '')} for n in full_doc['structure']], indent=2)}
    
    Return the questions as a JSON list of strings.
    """
    
    response = llm_completion(settings, settings.rag_model, query_prompt)
    queries = extract_json(response)
    
    if not isinstance(queries, list) or len(queries) < 10:
        print("Error generating queries. Got:", queries)
        return

    queries = queries[:10]
    results = []

    # 2. Process each query
    for i, query in enumerate(queries):
        print(f"Processing Query {i+1}/10: {query}")
        
        # Expected Answer (Ground Truth) - Use full context if possible, or just a direct LLM call with doc info
        # To be safe and high quality, I'll provide the LLM with the most relevant sections directly for the "expected" answer
        # but for the "expected" one I'll let it see more if needed.
        
        # Actually, for "expected answer", I'll just ask the LLM to answer based on the WHOLE doc structure and text.
        # Since I can't pass the whole text easily, I'll use the most relevant text but without the RAG constraints.
        
        # RAG Answer
        print(f"  - Getting RAG answer...")
        node_ids = select_relevant_nodes(settings, tree_toon, query)
        context_texts = find_node_text(full_doc.get("structure", []), node_ids)
        rag_answer = generate_final_answer(settings, context_texts, query)
        
        # Expected Answer
        print(f"  - Getting expected answer...")
        # For expected answer, I'll give it the same context but maybe label it as ground truth?
        # Or better, I'll ask the LLM to provide the "ideal" answer given the document.
        expected_prompt = f"""
        You are a gold-standard question-answering system. Based on the document provided in the context, provide the most accurate and comprehensive answer to the query.
        
        CONTEXT (Relevant Sections):
        {" ".join(context_texts)}
        
        QUERY: {query}
        
        Provide a concise but complete answer.
        """
        expected_answer = llm_completion(settings, settings.rag_model, expected_prompt)
        
        results.append({
            "query": query,
            "expected_answer": expected_answer,
            "rag_answer": rag_answer,
            "nodes_selected": node_ids
        })

    # 3. Save to TXT
    print("Saving results to rag_evaluation.txt...")
    with open("rag_evaluation.txt", "w") as f:
        for i, res in enumerate(results):
            f.write(f"QUERY {i+1}: {res['query']}\n")
            f.write(f"EXPECTED ANSWER: {res['expected_answer']}\n")
            f.write(f"RAG ANSWER: {res['rag_answer']}\n")
            f.write(f"NODES SELECTED: {', '.join(res['nodes_selected'])}\n")
            f.write("-" * 80 + "\n\n")

    print("Done!")

if __name__ == "__main__":
    generate_evaluation()
