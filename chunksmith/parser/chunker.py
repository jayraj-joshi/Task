"""Tag pages with physical_index markers and split into token-budget groups."""

from __future__ import annotations

import math
from typing import List, Tuple

from chunksmith.llm_support.client import count_tokens


def build_tagged_page_strings(
    page_list: List[Tuple[str, int]],
    *,
    start_index: int = 1,
    model: str | None = None,
) -> Tuple[List[str], List[int]]:
    """
    Wrap each page's text in ``<physical_index_N>`` tags.

    Token counts are computed on the **tagged** strings (same as original PageIndex).
    """
    page_contents: List[str] = []
    token_lengths: List[int] = []
    for i, (page_text, _tok_unused) in enumerate(page_list):
        page_num = start_index + i
        wrapped = (
            f"<physical_index_{page_num}>\n{page_text}\n<physical_index_{page_num}>\n\n"
        )
        page_contents.append(wrapped)
        token_lengths.append(count_tokens(wrapped, model))
    return page_contents, token_lengths


def page_list_to_group_text(
    page_contents: List[str],
    token_lengths: List[int],
    *,
    max_tokens: int = 20000,
    overlap_page: int = 1,
) -> List[str]:
    """
    Split tagged page strings into groups that each stay near ``max_tokens`` total.

    Mirrors the original PageIndex grouping logic (with overlap between groups).
    """
    num_tokens = sum(token_lengths)
    if num_tokens <= max_tokens:
        return ["".join(page_contents)]

    subsets: List[str] = []
    current_subset: List[str] = []
    current_token_count = 0
    expected_parts_num = math.ceil(num_tokens / max_tokens)
    average_tokens_per_part = math.ceil(((num_tokens / expected_parts_num) + max_tokens) / 2)

    for i, (page_content, page_tokens) in enumerate(zip(page_contents, token_lengths)):
        if current_token_count + page_tokens > average_tokens_per_part:
            subsets.append("".join(current_subset))
            overlap_start = max(i - overlap_page, 0)
            current_subset = list(page_contents[overlap_start:i])
            current_token_count = sum(token_lengths[overlap_start:i])
        current_subset.append(page_content)
        current_token_count += page_tokens

    if current_subset:
        subsets.append("".join(current_subset))
    return subsets
