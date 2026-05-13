
import os
from pathlib import Path
from chunksmith import build_outline_from_pdf, load_settings, toon
import json

def process():
    settings = load_settings()
    pdf_path = Path("pdf/alltransformer.pdf")
    
    print(f"[*] Processing {pdf_path}...")
    result = build_outline_from_pdf(
        pdf_path,
        settings,
        add_text=True,
        assign_node_ids=True,
        add_summary=True,
        add_word_range=True,
        generate_doc_summary=True
    )

    # Save JSON
    with open("alltransformer_output.json", "w") as f:
        json.dump(result, f, indent=2)
    
    # Save TOON
    def _strip_text(obj):
        if isinstance(obj, dict):
            return {k: _strip_text(v) for k, v in obj.items() if k != "text"}
        if isinstance(obj, list):
            return [_strip_text(x) for x in obj]
        return obj

    toon_data = toon.encode(_strip_text(result))
    with open("alltransformer_output.toon", "w") as f:
        f.write(toon_data)
    
    print("Done!")

if __name__ == "__main__":
    process()
