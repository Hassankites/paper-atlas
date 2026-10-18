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


_EDGE_PUNCT = ".,;:!?()[]{}\"'“”‘’"


def _word_key(word: str) -> str:
    """Strip edge punctuation so a quote without its full stop still matches."""
    return word.strip(_EDGE_PUNCT)


def _group_by_line(rects: list[pymupdf.Rect]) -> list[pymupdf.Rect]:
    """Merge word rectangles into one rectangle per visual line.

    Words on the same baseline but in different columns stay apart: a union
    across the gutter produces the giant block users rightly complain about.
    12 pt covers the widest inter-word gap in justified text and still splits
    the narrowest two-column gutter we have seen.
    """
    lines: list[pymupdf.Rect] = []
    for rect in rects:
        for index, line in enumerate(lines):
            same_baseline = abs(rect.y0 - line.y0) < 4
            near = rect.x0 - line.x1 < 12 and line.x0 - rect.x1 < 12
            if same_baseline and near:
                lines[index] = line | rect
                break
        else:
            lines.append(pymupdf.Rect(rect))
    return lines


def _first_cluster(lines: list[pymupdf.Rect]) -> list[pymupdf.Rect]:
    """Keep the first contiguous run of lines; drop repeats elsewhere on the page."""
    if not lines:
        return []
    ordered = sorted(lines, key=lambda rect: (round(rect.y0), rect.x0))
    cluster = [ordered[0]]
    for rect in ordered[1:]:
        if rect.y0 - cluster[-1].y1 <= 30:
            cluster.append(rect)
        else:
            break
    return cluster


def _canon(text: str) -> str:
    return " ".join(
        word for word in (_word_key(part) for part in normalize(text).split()) if word
    )


def page_text(page) -> str:
    """Reading-order text with hyphenated line breaks stitched."""
    return " ".join(word for _, word in _words(page))


def count_occurrences(page, quote: str) -> int:
    """How many times a quote appears on a page, after normalisation."""
    needle = _canon(quote)
    if not needle:
        return 0
    return _canon(page_text(page)).count(needle)


def _plausible(rects: list[pymupdf.Rect]) -> bool:
    """Reject matches whose 'lines' jump far down the page: a false pairing."""
    ordered = sorted(rects, key=lambda rect: (round(rect.y0), rect.x0))
    for previous, current in zip(ordered, ordered[1:]):
        if current.y0 - previous.y1 > 30:
            return False
    return True


def find_rects(page, quote: str) -> list[pymupdf.Rect]:
    """Return rectangles covering `quote`, one per line, or an empty list."""
    direct = page.search_for(quote)
    if direct and _plausible(direct):
        return _first_cluster(_group_by_line(direct))

    target = [_word_key(word) for word in normalize(quote).split()]
    target = [word for word in target if word]
    if not target:
        return []

    words = _words(page)
    width = len(target)
    best: list[pymupdf.Rect] | None = None
    best_area: float | None = None
    for start in range(len(words) - width + 1):
        window = [_word_key(normalize(word)) for _, word in words[start : start + width]]
        if window != target:
            continue
        rects = [rect for rect, _ in words[start : start + width]]
        if not _plausible(rects):
            continue
        union = rects[0]
        for rect in rects[1:]:
            union = union | rect
        area = union.width * union.height
        if best_area is None or area < best_area:
            best_area, best = area, rects
    if best is None:
        return []
    return _first_cluster(_group_by_line(best))


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
