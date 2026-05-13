"""Prompt templates for flat outline extraction (no-TOC path)."""

# Appended to init/continue instructions when ``add_summary`` is enabled (same completion as outline rows).
SUMMARY_INSTRUCTION = """
Each row must also include "summary" (string): provide a detailed and dynamic summary that is 
approximately 30% of the length of the original section text. The summary should capture 
key concepts, specific data points, and context using only information visible in the given 
excerpt (no outside knowledge). Ensure the summary length scales with the section's importance 
and detail."""

# Appended when ``add_word_range=True``: one verbatim alignment string per row (no word indices).
ANCHOR_INSTRUCTION = """
When section anchors are requested in the **same** API response, every row must include the usual outline keys
(structure, title, physical_index, and "summary" only if that was also requested) **plus**:

  • ``split_document_anchor`` (string) — a **short verbatim substring** copied from the **Given text** excerpt below
    (the text after ``Given text`` + newline + ``:``). Use text at or immediately after where that section begins
    in this excerpt (e.g. heading like ``1 Introduction``, ``Abstract``, ``3.2 Attention``). Used to locate and
    verify the section start in the excerpt; it must appear exactly as in the Given text.

Apply this on **every** row for this message. For **continue** calls, anchors refer only to the **current** excerpt
(the new Given text in this message), not to prior parts."""

TOC_INIT_SYSTEM = """
You are an expert in extracting hierarchical tree structure. Generate the tree structure of the document.

**Extraction Strategy:** Be highly granular. Capture ALL headings, sub-headings, and distinct sections, even if they lack numeric prefixes. If a page contains multiple distinct topics (e.g., "March 2024 Summary", "June 2023 Summary"), each MUST be captured as a separate row in the hierarchy. Do not skip minor sections or group large page ranges into a single node if sub-headings are present.

structure: numeric index, e.g. "1", "1.1", "1.2", "1.2.1", "1.2.2", "1.2.3", "1.2.4", "1.2.5", "1.2.6", "1.2.7", "1.2.8", "1.2.9", "1.2.10".
Tags <physical_index_X> in the given text mark where PDF page X begins. Long PDFs are split into multiple excerpts; this message is the first excerpt only.
Several sections may start on the same page—that is normal; set each row's physical_index from the tag nearest that section's start.
**Important:** ``physical_index`` is always the **printed PDF page** from those tags only—never infer it from section numbers in headings (e.g. a section titled ``3 Model Architecture`` may start on page 2 if the ``<physical_index_2>`` block contains that heading).
Each section row must include: "structure" (string), "title" (string), and "physical_index"
(either an integer start page or a string tag like "<physical_index_5>").
If the prompt also includes appended instructions (e.g. per-section summaries or ``split_document_anchor`` on the excerpt),
include those fields on every row as specified there.
Return JSON only: a markdown code block ```json containing either a JSON array of rows in reading order,
or an object {"sections": [ ...rows... ]}."""

TOC_CONTINUE_SYSTEM = """
You are an expert in extracting hierarchical tree structure.
You are given the previous outline as JSON and the text of the current part of the document.
Continue the outline: add new rows only for sections that appear in the current part.

**Extraction Strategy:** Maintain high granularity. Capture ALL sub-headings and distinct content blocks. If you see a transition to a new topic (e.g., "March 2024 Summary"), create a new row even if it's on the same page as the parent heading. Do not consolidate multiple sub-sections into a single parent node.

structure: numeric index, e.g. "1", "1.1", "1.2", "1.2.1", "1.2.2", "1.2.3", "1.2.4", "1.2.5", "1.2.6", "1.2.7", "1.2.8", "1.2.9", "1.2.10".
Tags <physical_index_X> in the given text mark where PDF page X begins. The start of this excerpt often overlaps the end of the prior excerpt (the same pages can appear again)—use the tags to assign physical_index and do **not** duplicate sections already present in the previous outline JSON.
Several sections may start on the same page; that is normal.
Each row: "structure" (string), "title" (string), "physical_index" (int or "<physical_index_N>" string).
``physical_index`` must be the PDF page from ``<physical_index_N>`` tags only, not from numeric prefixes in section titles.
When ``split_document_anchor`` is requested, it must be copied from **this** message's Given text excerpt only.
If the prompt also includes appended instructions (e.g. summaries or anchors), include those fields on each new row.
Return JSON only: ```json with either an array of only the additional rows, or {"sections": [ ... ]}."""



def build_doc_description_prompt(structure_json: str) -> str:
    """User message for a standalone completion after the TOC tree exists (not mixed with outline extraction)."""
    return f"""You are an expert in generating descriptions for a document.
You are given a structure of a document. Your task is to generate a comprehensive and detailed summary (2-3 paragraphs) for the document, highlighting the main purpose, key findings, and overall organization. The summary should be informative enough to give a deep understanding of the document's content.

Document Structure:
{structure_json}

Directly return the detailed summary, do not include any other text."""


NODE_SELECTION_SYSTEM = """
You are a retrieval assistant specialized in hierarchical document analysis. 
Your task is to identify all relevant sections (node IDs) from a document tree that might help answer a specific user query.

Guidelines:
1. **Focus on Sub-Nodes**: Always prefer specific sub-nodes (leaf nodes) that match the query.
2. **Numerical Data**: Look for specific numerical values (e.g., "239,000", "2.5 percent") in the summaries. **IMPORTANT**: Ignore dates in titles or anchors (like "2024" or "2023") when looking for "numbers" or "stats".
3. **Handle Spelling**: Treat "labour" and "labor" as identical.
4. **Keyword Matching**: Select a node if its title or summary contains direct keywords or synonyms.
5. **Output Format**: Return ONLY a valid JSON list of strings (node IDs). Ensure strings are in double quotes. 
   - Correct: ["0001", "0002"]
"""


def build_node_selection_prompt(tree_toon: str, query: str) -> str:
    """Combines node selection instructions with document tree and query."""
    return f"""{NODE_SELECTION_SYSTEM}

DOCUMENT TREE (TOON format):
{tree_toon}

USER QUERY: {query}

Return the JSON list of relevant node IDs:"""


RAG_ANSWER_SYSTEM = """
You are a helpful and accurate assistant. Your task is to answer the user's query using ONLY the provided context from a document.

Guidelines:
1. Use the provided context to construct a comprehensive and direct answer.
2. If the context contains specific data points, numbers, or names, include them.
3. If the answer is not contained in the context or the query cannot be satisfied, strictly return the exact phrase: "No relevant document found".
4. Maintain a professional and objective tone.
5. Do not use outside knowledge or hallucinate details.
"""


def build_rag_answer_prompt(query: str, context: str) -> str:
    """Combines query with retrieved context for final answer generation."""
    return f"""{RAG_ANSWER_SYSTEM}

CONTEXT:
{context}

USER QUERY: {query}

ANSWER:"""
