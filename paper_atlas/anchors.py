"""Locate a verbatim quote in a PDF, surviving the traps of real papers.

Two-column layouts, hyphenated line breaks and ligatures all break naive
`page.search_for`, and a coordinate the model guessed is worse than no
annotation at all. Everything here returns rectangles or nothing.

Two rules keep the rectangles honest, both learned from a review that caught
a highlight painting the next paragraph: a hyphen inside a number is a sign,
never a typographic break, and one quad covers only the text band of its line,
so a tall glyph (a formula, a superscript) cannot stretch it over the next
line.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pymupdf


_LIGATURES = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\ufb05": "ft",
    "\ufb06": "st",
}

# Typographic dashes are the same separator as "-" for matching purposes; the
# minus sign is the one that must never be confused with a hyphen.
_DASHES = "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"

# A letter immediately before a hyphen and a newline: a real word break.
_LINE_BREAK_HYPHEN = re.compile(r"([^\W\d_])-\s*\n\s*([^\W\d_])")


def normalize(text: str) -> str:
    """Collapse whitespace, unpack ligatures and undo hyphenated line breaks."""
    for ligature, expansion in _LIGATURES.items():
        text = text.replace(ligature, expansion)
    text = text.replace("\u00ad", "")
    for dash in _DASHES:
        text = text.replace(dash, "-")
    # Only a letter can be split by a line break; "10-\n20" keeps both halves.
    text = _LINE_BREAK_HYPHEN.sub(r"\1\2", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


@dataclass(frozen=True)
class Segment:
    """One matchable word, possibly split over two lines by a hyphen."""

    rects: tuple[pymupdf.Rect, ...]
    text: str


def _segments(page) -> list[Segment]:
    """Words in reading order, with line-end hyphenated pairs joined.

    The two halves keep their own rectangles: unioning them produces a box
    spanning the gutter between the end of one line and the start of the next,
    which is how a highlight ends up covering unrelated text.
    """
    raw = [(pymupdf.Rect(item[:4]), item[4]) for item in page.get_text("words")]
    segments: list[Segment] = []
    for rect, word in raw:
        if segments:
            last = segments[-1]
            split = (
                last.text.endswith("-")
                and word
                and not any(char.isdigit() for char in last.text)
                and not any(char.isdigit() for char in word)
                and rect.y0 > last.rects[-1].y1 - 2  # next line, not same line
            )
            if split:
                segments[-1] = Segment(last.rects + (rect,), last.text[:-1] + word)
                continue
        segments.append(Segment((rect,), word))
    return segments


_EDGE_PUNCT = ".,;:!?()[]{}\"'“”‘’"


def _word_key(word: str) -> str:
    """Strip edge punctuation so a quote without its full stop still matches."""
    return word.strip(_EDGE_PUNCT)


def _match_key(word: str) -> str:
    """Key for matching: hyphens are ignored in words, kept in numbers.

    `pre-trained` must still match `pretrained`, but `-1` must never match `1`:
    deleting the sign would certify a changed scientific number as a verbatim
    quote.
    """
    key = _word_key(normalize(word)).casefold()
    if any(char.isdigit() for char in key):
        return key
    return key.replace("-", "")


def _canon(text: str) -> str:
    return " ".join(
        part for part in (_match_key(part) for part in normalize(text).split()) if part
    )


def _line_band(rects: list[pymupdf.Rect]) -> tuple[float, float]:
    """Vertical band shared by the ordinary text on a line.

    Members far taller than the shortest one are clipped: an inline formula or
    superscript must not stretch the quad over the following line.
    """
    heights = sorted(rect.height for rect in rects)
    if not heights:
        return 0.0, 0.0
    limit = heights[0] * 1.4
    keep = [rect for rect in rects if rect.height <= limit]
    if not keep:
        keep = rects
    return min(rect.y0 for rect in keep), max(rect.y1 for rect in keep)


def _same_line(rect: pymupdf.Rect, union: pymupdf.Rect) -> bool:
    """True when two boxes sit on one baseline, whatever their glyph heights.

    Comparing top edges misreads an inline formula or a raised superscript as a
    line of its own; vertical overlap survives that, and adjacent lines do not
    overlap at all.
    """
    overlap = min(rect.y1, union.y1) - max(rect.y0, union.y0)
    return overlap >= 0.5 * min(rect.height, union.height)


def _line_groups(rects: list[pymupdf.Rect]) -> list[list[pymupdf.Rect]]:
    groups: list[list[pymupdf.Rect]] = []
    for rect in rects:
        for group in groups:
            union = group[0]
            for member in group[1:]:
                union = union | member
            # 12 pt covers the widest inter-word gap in justified text and still
            # splits the narrowest two-column gutter we have seen.
            near = rect.x0 - union.x1 < 12 and union.x0 - rect.x1 < 12
            if _same_line(rect, union) and near:
                group.append(rect)
                break
        else:
            groups.append([rect])
    return groups


def _group_by_line(rects: list[pymupdf.Rect]) -> list[pymupdf.Rect]:
    """One rectangle per visual line, clipped to that line's text band."""
    lines: list[pymupdf.Rect] = []
    for group in _line_groups(rects):
        union = group[0]
        for member in group[1:]:
            union = union | member
        top, bottom = _line_band(group)
        lines.append(pymupdf.Rect(union.x0, top, union.x1, bottom))
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


def _text_inside(page, rects: list[pymupdf.Rect]) -> str:
    return " ".join(page.get_textbox(rect) for rect in rects)


def _trim_to_one(page, lines: list[pymupdf.Rect], quote: str) -> list[pymupdf.Rect]:
    """Cut a cluster back to a single occurrence of the quote.

    Two adjacent lines can hold the same sentence twice; merging them because
    they are close would paint one annotation over both.
    """
    needle = _canon(quote)
    if not needle:
        return lines
    trimmed = list(lines)
    while len(trimmed) > 1 and _canon(_text_inside(page, trimmed)).count(needle) > 1:
        trimmed.pop()
    return trimmed


def page_text(page) -> str:
    """Reading-order text with hyphenated line breaks stitched."""
    return " ".join(segment.text for segment in _segments(page))


def count_occurrences(page, quote: str) -> int:
    """How many whole-word matches of a quote a page contains.

    Case-insensitive, like PyMuPDF's search, and word-bounded, so `method`
    does not count inside `methodology`.
    """
    needle = _canon(quote)
    if not needle:
        return 0
    haystack = _canon(page_text(page))
    return len(re.findall(rf"(?<!\w){re.escape(needle)}(?!\w)", haystack))


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
        rects = _trim_to_one(page, _first_cluster(_group_by_line(direct)), quote)
        if rects:
            return rects

    target = [_match_key(word) for word in normalize(quote).split()]
    target = [word for word in target if word]
    if not target:
        return []

    segments = _segments(page)
    width = len(target)
    best: list[pymupdf.Rect] | None = None
    best_area: float | None = None
    for start in range(len(segments) - width + 1):
        window = segments[start : start + width]
        if [_match_key(segment.text) for segment in window] != target:
            continue
        rects = [rect for segment in window for rect in segment.rects]
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
    return _trim_to_one(page, _first_cluster(_group_by_line(best)), quote)


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
