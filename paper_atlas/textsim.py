"""Detect a comment that Zotero would silently erase.

Zotero's importer drops a comment when it is approximately equal to the text
it annotates (`textApproximatelyEqual` in the document worker): normalised
edit distance below roughly 10% of the comment length. A `[label]` prefix is
far below that for any long quote, so a template that echoes the quote comes
back empty in the reader.
"""

from __future__ import annotations

import re

SIMILARITY_THRESHOLD = 0.1


def normalized(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _levenshtein(a: str, b: str) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, 1):
        current = [i]
        for j, char_b in enumerate(b, 1):
            insert = current[j - 1] + 1
            delete = previous[j] + 1
            replace = previous[j - 1] + (char_a != char_b)
            current.append(min(insert, delete, replace))
        previous = current
    return previous[-1]


def too_similar(comment: str, quote: str) -> bool:
    """True when Zotero would treat this comment as a copy of the highlight."""
    comment_text = normalized(comment)
    quote_text = normalized(quote)
    if not comment_text or not quote_text:
        return False
    distance = _levenshtein(comment_text, quote_text)
    return distance < SIMILARITY_THRESHOLD * len(comment_text)
