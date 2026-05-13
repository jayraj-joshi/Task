import json
import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(os.getcwd())

from chunksmith import build_outline_from_pdf, load_settings
from chunksmith.toon import encode

def test_detailed_indexing():
    pdf_path = "pdf/First10.pdf"
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found.")
        return

    print(f"[*] Starting indexing for {pdf_path} with new detailed settings...")
    settings = load_settings()
    
    try:
        # We'll use the core function directly
        result = build_outline_from_pdf(
            pdf_path,
            settings,
            add_text=True,
            assign_node_ids=True,
            add_summary=True,
            add_word_range=True,
            generate_doc_summary=True
        )
        
        print("\n" + "="*50)
        print("DOCUMENT DESCRIPTION:")
        print(result.get("doc_description", "N/A"))
        print("="*50)
        
        print("\nTOP-LEVEL SECTION SUMMARIES:")
        for node in result.get("structure", []):
            print(f"\n[ {node.get('title')} ]")
            print(f"Summary: {node.get('summary')}")
            
        # Save to a test output file
        output_file = "scratch/test_detailed_output.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n[*] Full result saved to {output_file}")

    except Exception as e:
        print(f"Error during indexing: {e}")

if __name__ == "__main__":
    test_detailed_indexing()
