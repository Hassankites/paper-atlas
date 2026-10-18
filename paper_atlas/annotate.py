"""Write a map into the PDF as annotated highlights Zotero will import.

Rules this module enforces, because each one already cost a debugging
session: the colour is only ever the standard `/C` array (a string in
`/Zotero:Color` silently turns highlights black), the comment is never a
copy of the highlighted text (Zotero erases those), and every annotation
carries `/Zotero:Key` so a second run can tell it was already written.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from paper_atlas import anchors

AUTHOR = "Paper Atlas"
KEY_PREFIX = "pa-"
BACKUP_SUFFIX = ".paper-atlas.bak.pdf"

COLORS = {
    "claim": "#ffd400",
    "chain": "#f19837",
    "choice": "#5fb236",
    "figure": "#2ea8e5",
    "limit": "#ff6666",
}

LABELS = {
    "zh": {
        "claim": "主张",
        "chain": "链条",
        "choice": "选择",
        "figure": "图表",
        "limit": "存疑",
        "alternative": "本可以",
        "solves": "解决",
        "cost": "代价",
        "supports": "支撑",
        "caveat": "没证明",
        "sep": " ｜ ",
    },
    "en": {
        "claim": "Claim",
        "chain": "Chain",
        "choice": "Choice",
        "figure": "Figure",
        "limit": "Open question",
        "alternative": "could have",
        "solves": "solves",
        "cost": "costs",
        "supports": "supports",
        "caveat": "does not prove",
        "sep": " | ",
    },
}


@dataclass(frozen=True)
class Planned:
    id: str
    role: str
    color: str
    comment: str
    page: int
    quote: str


def _pdf_string(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return f"({escaped})"


def hex_to_rgb(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) / 255 for index in (0, 2, 4))


def _clip(text: str, limit: int = 200) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _comment(role: str, entry: dict, labels: dict) -> str:
    separator = labels["sep"]
    if role == "claim":
        body = entry.get("text", "")
    elif role == "chain":
        body = f"{entry.get('id', '')} {entry.get('text', '')}".strip()
    elif role == "choice":
        body = separator.join(
            [
                f"{labels['alternative']}: {entry.get('alternative', '—')}",
                f"{labels['solves']}: {entry.get('solves', '—')}",
                f"{labels['cost']}: {entry.get('cost', '—')}",
            ]
        )
    elif role == "figure":
        body = separator.join(
            [
                f"{labels['supports']}: {entry.get('supports', '—')}",
                f"{labels['caveat']}: {entry.get('caveat', '—')}",
            ]
        )
    else:
        body = entry.get("text", "")
    return _clip(f"[{labels[role]}] {body}")


def plan(map_dict: dict, doc, lang: str = "zh") -> list[Planned]:
    labels = LABELS.get(lang, LABELS["zh"])
    paper_key = (map_dict.get("paper") or {}).get("zotero_key") or "map"
    planned: list[Planned] = []

    def add(role: str, entry_id: str, entry: dict, quote: str) -> None:
        planned.append(
            Planned(
                id=f"{KEY_PREFIX}{paper_key}-{entry_id}",
                role=role,
                color=COLORS[role],
                comment=_comment(role, entry, labels),
                page=int(entry.get("page", 0)),
                quote=quote,
            )
        )

    claim = map_dict.get("claim") or {}
    if claim:
        add("claim", "claim", claim, claim.get("quote", ""))
    for index, entry in enumerate(map_dict.get("chain") or [], 1):
        add("chain", entry.get("id") or f"c{index}", entry, entry.get("quote", ""))
    for index, entry in enumerate(map_dict.get("choices") or [], 1):
        add("choice", entry.get("id") or f"d{index}", entry, entry.get("quote", ""))
    for index, entry in enumerate(map_dict.get("figures") or [], 1):
        add(
            "figure",
            entry.get("label", f"fig{index}").lower().replace(" ", "-"),
            entry,
            entry.get("caption_quote", ""),
        )
    for index, entry in enumerate(map_dict.get("limits") or [], 1):
        add("limit", f"l{index}", entry, entry.get("quote", ""))
    return planned


def _our_keys(doc) -> set[str]:
    keys: set[str] = set()
    for page in doc:
        for annot in page.annots() or []:
            kind, value = doc.xref_get_key(annot.xref, "Zotero:Key")
            if kind == "string" and value.startswith(KEY_PREFIX):
                keys.add(value)
    return keys


def _remove_ours(doc) -> None:
    for page in doc:
        for annot in list(page.annots() or []):
            kind, value = doc.xref_get_key(annot.xref, "Zotero:Key")
            if kind == "string" and value.startswith(KEY_PREFIX):
                page.delete_annot(annot)


def apply(
    pdf_path: Path, planned: list[Planned], doc, force: bool = False
) -> dict:
    path = Path(pdf_path)
    backup = path.with_name(path.stem + BACKUP_SUFFIX)
    if not backup.exists():
        shutil.copy2(path, backup)

    if force:
        _remove_ours(doc)
    existing = _our_keys(doc)

    added = 0
    skipped = 0
    missing: list[str] = []
    for item in planned:
        if item.id in existing:
            skipped += 1
            continue
        found = anchors.locate(doc, item.page, item.quote)
        if found is None:
            missing.append(item.id)
            continue
        page_index, rects = found
        page = doc[page_index]  # keep the reference: a temporary page unbinds the annot
        annot = page.add_highlight_annot(rects[0])
        annot.set_colors(stroke=hex_to_rgb(item.color))
        annot.set_info(content=item.comment, title=AUTHOR)
        annot.update()
        doc.xref_set_key(annot.xref, "Zotero:AuthorName", _pdf_string(AUTHOR))
        doc.xref_set_key(annot.xref, "Zotero:Key", _pdf_string(item.id))
        added += 1

    doc.saveIncr()
    return {"added": added, "skipped": skipped, "missing": missing}
