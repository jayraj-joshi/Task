
import json
import tiktoken
import os

def count_tokens(text, model="gpt-4o"):
    try:
        enc = tiktoken.encoding_for_model(model)
    except:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))

def get_prompt(tree_content, query, format_name):
    return f"""
You are a precision retrieval assistant. Below is a hierarchical summary (in {format_name} format) of a document.
Your task is to identify which sections (node IDs) are most relevant to answer the user's query.

DOCUMENT TREE:
{tree_content}

USER QUERY: {query}

Instructions:
1. Analyze the query and the summaries in the tree.
2. Return a JSON list of node IDs (strings) that likely contain the information needed to answer the query.
3. Be specific. If sub-sections are available, select the most relevant sub-sections.
4. Return ONLY the JSON list of strings.

Example Output:
["0003", "0009"]
"""

def _strip_text(obj):
    if isinstance(obj, dict):
        return {k: _strip_text(v) for k, v in obj.items() if k != "text"}
    if isinstance(obj, list):
        return [_strip_text(x) for x in obj]
    return obj

def compare():
    # File paths
    files = {
        "First10": {
            "json": "First10_output.json",
            "toon": "First10_output.toon"
        },
        "AllTransformer": {
            "json": "alltransformer_output.json",
            "toon": "alltransformer_output.toon"
        }
    }

    # 5 Queries each
    queries = [
        # First10
        ("First10", "What are the projected real GDP growth rates for 2024 and 2025?"),
        ("First10", "How has the unemployment rate projection changed compared to the previous summary?"),
        ("First10", "What is the median projection for the federal funds rate at the end of 2024?"),
        ("First10", "Summarize the projections for PCE inflation and core PCE inflation."),
        ("First10", "How do the projections for 2026 differ from the longer-run projections?"),
        # AllTransformer
        ("AllTransformer", "What is the complexity of Scaled Dot-Product Attention?"),
        ("AllTransformer", "How does the Multi-Head Attention mechanism differ from single-head attention?"),
        ("AllTransformer", "What are the experimental results on the WMT 2014 translation task?"),
        ("AllTransformer", "Explain the Positional Encoding used in the model."),
        ("AllTransformer", "What are the advantages of the Transformer architecture over RNNs?")
    ]

    results = []

    for doc_name, query in queries:
        json_path = files[doc_name]["json"]
        toon_path = files[doc_name]["toon"]

        if not os.path.exists(json_path) or not os.path.exists(toon_path):
            continue

        with open(json_path, "r") as f:
            data = json.load(f)
            stripped_data = _strip_text(data)
            json_tree = json.dumps(stripped_data, indent=2)
        
        with open(toon_path, "r") as f:
            toon_tree = f.read()

        json_prompt = get_prompt(json_tree, query, "JSON")
        toon_prompt = get_prompt(toon_tree, query, "TOON")

        json_tokens = count_tokens(json_prompt)
        toon_tokens = count_tokens(toon_prompt)

        results.append({
            "doc": doc_name,
            "query": query,
            "json_tokens": json_tokens,
            "toon_tokens": toon_tokens,
            "diff": json_tokens - toon_tokens,
            "reduction_pct": (json_tokens - toon_tokens) / json_tokens * 100
        })

    with open("comparison_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("Updated comparison_results.json with 10 queries (5 per PDF).")

if __name__ == "__main__":
    compare()
