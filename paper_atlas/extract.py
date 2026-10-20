"""Turn a PDF into page blocks, section headings, figure captions and crops."""

from __future__ import annotations

import re
from pathlib import Path

import pymupdf

CAPTION_RE = re.compile(r"^(Figure|Fig\.|Table|图|表)\s*(\d+)\s*[:：.]", re.IGNORECASE)
# Chinese journals commonly write 图1 标题 with no colon at all.
CJK_CAPTION_RE = re.compile(r"^(图|表)\s*(\d+)\s+")
# ...and prose commonly opens a sentence the same way: 图1 所示的结构……
_CJK_PROSE = ("所示", "显示", "展示", "给出", "可以看", "如图", "见表", "见图", "中可")
HEADING_RE = re.compile(r"^\d+(\.\d+)*\s+\S")
# A caption is one paragraph; 300 characters cut off the long ones (Adam's
# Figure 4 is 400+), which silently lost the figure.
MAX_CAPTION = 800


def _caption_match(text: str):
    """The caption match for a block, or None when the block is prose."""
    match = CAPTION_RE.match(text)
    if match:
        return match if len(text) <= MAX_CAPTION else None
    match = CJK_CAPTION_RE.match(text)
    if not match or len(text) > 80:
        return None
    if any(marker in text for marker in _CJK_PROSE):
        return None
    return match


def _page_blocks(page) -> list[dict]:
    blocks: list[dict] = []
    for raw in page.get_text("dict")["blocks"]:
        if raw.get("type") != 0:
            continue
        lines = ["".join(span["text"] for span in line["spans"]) for line in raw["lines"]]
        text = " ".join(line.strip() for line in lines if line.strip()).strip()
        if not text:
            continue
        sizes = [span["size"] for line in raw["lines"] for span in line["spans"]]
        blocks.append(
            {
                "bbox": [round(value, 2) for value in raw["bbox"]],
                "text": text,
                "size": round(max(sizes), 2),
            }
        )
    blocks.sort(key=lambda block: (block["bbox"][1], block["bbox"][0]))
    return blocks


def _body_size(pages: list[dict]) -> float:
    weight: dict[int, int] = {}
    for page in pages:
        for block in page["blocks"]:
            key = round(block["size"])
            weight[key] = weight.get(key, 0) + len(block["text"])
    if not weight:
        return 0.0
    return float(max(weight, key=weight.get))


def is_textless(structure: dict, min_chars: int = 200) -> bool:
    """True for a scanned PDF: no text layer to anchor anything to."""
    total = sum(
        len(block["text"]) for page in structure["pages"] for block in page["blocks"]
    )
    return total < min_chars


def extract_structure(pdf_path: Path) -> dict:
    doc = pymupdf.open(str(pdf_path))
    pages = []
    for index, page in enumerate(doc):
        pages.append(
            {
                "index": index,
                "width": round(page.rect.width, 2),
                "height": round(page.rect.height, 2),
                "blocks": _page_blocks(page),
            }
        )
    doc.close()

    body = _body_size(pages)
    sections: list[dict] = []
    figures: list[dict] = []
    for page in pages:
        for block in page["blocks"]:
            text = block["text"]
            match = _caption_match(text)
            if match:
                kind = match.group(1).lower()
                is_figure = kind in ("figure", "fig.", "图")
                label = f"{'Figure' if is_figure else 'Table'} {match.group(2)}"
                figures.append(
                    {
                        "label": label,
                        "page": page["index"],
                        "caption": text,
                        "bbox": block["bbox"],
                    }
                )
                continue
            looks_like_heading = block["size"] >= body * 1.15 and len(text) < 120
            numbered = HEADING_RE.match(text) is not None and len(text) < 90
            if looks_like_heading or numbered:
                sections.append(
                    {"title": text, "page": page["index"], "bbox": block["bbox"]}
                )

    return {"pages": pages, "sections": sections, "figures": figures}


def _region_top(structure: dict, figure: dict, caption: pymupdf.Rect) -> float:
    blocks = structure["pages"][figure["page"]]["blocks"]
    above = [
        block["bbox"][3]
        for block in blocks
        if block["bbox"][3] <= caption.y0 + 1 and block["bbox"] != figure["bbox"]
    ]
    return max(above, default=0.0)


def _visual_above(page, caption: pymupdf.Rect, region_top: float):
    candidates = []
    for drawing in page.get_drawings():
        rect = pymupdf.Rect(drawing["rect"])
        if rect.y0 >= region_top and rect.y1 <= caption.y0 + 2:
            if rect.width > 30 and rect.height > 20:
                candidates.append(rect)
    for info in page.get_image_info():
        rect = pymupdf.Rect(info["bbox"])
        if rect.y0 >= region_top and rect.y1 <= caption.y0 + 2:
            candidates.append(rect)
    if not candidates:
        return None
    union = candidates[0]
    for rect in candidates[1:]:
        union |= rect
    return union


def render_figures(
    structure: dict, pdf_path: Path, out_dir: Path, dpi: int = 160
) -> list[dict]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(str(pdf_path))
    rendered = []
    for figure in structure["figures"]:
        page = doc[figure["page"]]
        caption = pymupdf.Rect(figure["bbox"])
        visual = _visual_above(page, caption, _region_top(structure, figure, caption))
        if visual is None:
            figure["crop"] = None
        else:
            clip = pymupdf.Rect(
                min(visual.x0, caption.x0) - 4,
                min(visual.y0, caption.y0) - 4,
                max(visual.x1, caption.x1) + 4,
                caption.y1 + 4,
            ) & page.rect
            pix = page.get_pixmap(clip=clip, dpi=dpi)
            name = figure["label"].lower().replace(" ", "-") + ".png"
            target = out_dir / name
            pix.save(target)
            figure["crop"] = str(target)
        rendered.append(figure)
    doc.close()
    return rendered
