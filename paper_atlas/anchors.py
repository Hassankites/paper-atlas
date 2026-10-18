"""Locate a verbatim quote in a PDF, surviving the traps of real papers.

Two-column layouts, hyphenated line breaks and ligatures all break naive
`page.search_for`, and a coordinate the model guessed is worse than no
annotation at all. Everything here returns rectangles or nothing.
"""

from __future__ import annotations

import re

import pymupdf


def normalize(text: str) -> str:
    """Collapse whitespace and undo hyphenated line breaks."""
    text = text.replace("\u00ad", "")
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    text = text.replace("-\n", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _words(page) -> list[tuple[pymupdf.Rect, str]]:
    """Words in reading order with hyphenated pairs joined."""
    raw = [(pymupdf.Rect(item[:4]), item[4]) for item in page.get_text("words")]
    joined: list[tuple[pymupdf.Rect, str]] = []
    for rect, word in raw:
        if joined and joined[-1][1].endswith("-") and word:
            previous_rect, previous_word = joined[-1]
            joined[-1] = (previous_rect | rect, previous_word[:-1] + word)
            continue
        joined.append((rect, word))
    return joined


def find_rects(page, quote: str) -> list[pymupdf.Rect]:
    """Return rectangles covering `quote`, or an empty list."""
    direct = page.search_for(quote)
    if direct:
        return direct

    target = normalize(quote).split()
    if not target:
        return []

    words = _words(page)
    width = len(target)
    for start in range(len(words) - width + 1):
        window = [normalize(word) for _, word in words[start : start + width]]
        if window == target:
            rect = words[start][0]
            for extra_rect, _ in words[start + 1 : start + width]:
                rect = rect | extra_rect
            return [rect]
    return []


def locate(
    doc, page_index: int, quote: str, tolerance_pages: int = 1
) -> tuple[int, list[pymupdf.Rect]] | None:
    """Find `quote` on `page_index`, then on neighbours within tolerance."""
    offsets = [0]
    for step in range(1, tolerance_pages + 1):
        offsets.extend([-step, step])
    for offset in offsets:
        index = page_index + offset
        if not 0 <= index < doc.page_count:
            continue
        rects = find_rects(doc[index], quote)
        if rects:
            return index, rects
    return None
