"""Check a map before a single annotation is written.

Three things are refused outright: a quote that is not in the paper, an
inference that does not say which sentence it came from, and two annotations
that would carry the same key. A fourth is refused softly: more highlights
than the density cap allows.

The rule underneath all of them is one source of truth per fact. A quote is
the paper's sentence; `inferred: true` means the wording is ours. An entry may
not claim both, because the reader cannot tell which half the paper said.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from paper_atlas import anchors, annotate, textsim

CAPS = {"normal": 20, "detailed": 30}
MAX_COMMENT = 240

_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")

# Fields whose numbers the reader will trust as the paper's.
_NUMBER_FIELDS = {
    "claim": ("text",),
    "chain": ("text",),
    "choices": ("choice", "alternative", "solves", "cost"),
    "figures": ("question", "supports", "key_numbers", "caveat"),
    "limits": ("text",),
    "pain": ("who", "symptom", "cost"),
    "novelty": ("what", "versus", "why"),
    "strength": ("text",),
    "concepts": ("gloss",),
}


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    highlight_count: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def _page(item: dict, key: str = "page") -> int:
    try:
        return int(item.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0


def _quote_error(
    doc, label: str, quote: str, page: int, report: Report, tolerance: int = 1
) -> tuple[int, list] | None:
    if not quote or not quote.strip():
        report.errors.append(f"{label}: missing quote")
        return None
    found = anchors.locate(doc, page, quote, tolerance_pages=tolerance)
    if found is None:
        report.errors.append(f"{label}: quote not found: {quote[:60]!r}")
        return None
    page_index, _ = found
    occurrences = anchors.count_occurrences(doc[page_index], quote)
    if occurrences > 1:
        report.errors.append(
            f"{label}: quote occurs {occurrences} times on p.{page_index + 1}; "
            "lengthen it until it is unique"
        )
    return found


def _basis_of(item: dict) -> str:
    return (item.get("basis_quote") or "").strip()


def _inference_error(doc, label: str, item: dict, page: int, report: Report) -> None:
    if not _basis_of(item):
        report.errors.append(f"{label}: inferred without basis_quote")
        return
    # The sentence an inference rests on may sit anywhere in the paper.
    _quote_error(
        doc,
        f"{label}.basis_quote",
        _basis_of(item),
        _page(item, "basis_page") if item.get("basis_page") is not None else page,
        report,
        tolerance=doc.page_count,
    )


def fill_pages(map_dict: dict, doc) -> list[str]:
    """Replace guessed pages with the pages the quotes are actually on.

    A page number the model worked out by counting is wrong often enough that
    every printed page should come from a successful locate. Returns the
    corrections it made, in the form `claim: 4 -> 3`.
    """
    corrections: list[str] = []

    def place(label: str, item: dict, quote_key: str, page_key: str, tolerance: int) -> None:
        quote = (item.get(quote_key) or "").strip()
        if not quote:
            return
        before = _page(item, page_key)
        found = anchors.locate(doc, before, quote, tolerance_pages=tolerance)
        if found is None:
            return
        if found[0] != before:
            corrections.append(f"{label}: p.{before + 1} -> p.{found[0] + 1}")
        item[page_key] = found[0]

    claim = map_dict.get("claim") or {}
    if claim:
        place("claim", claim, "quote", "page", 1)
    for index, item in enumerate(map_dict.get("chain") or [], 1):
        place(f"chain[{index}]", item, "quote", "page", 1)
    for index, item in enumerate(map_dict.get("choices") or [], 1):
        place(f"choices[{index}]", item, "quote", "page", 1)
        place(
            f"choices[{index}].basis",
            item,
            "basis_quote",
            "basis_page",
            doc.page_count,
        )
    for index, item in enumerate(map_dict.get("figures") or [], 1):
        place(f"figures[{index}]", item, "caption_quote", "page", 1)
    for index, item in enumerate(map_dict.get("limits") or [], 1):
        place(f"limits[{index}]", item, "quote", "page", 1)
    for section in ("pain", "novelty"):
        for index, item in enumerate(map_dict.get(section) or [], 1):
            place(f"{section}[{index}]", item, "quote", "page", 1)
    return corrections


def _echo_errors(map_dict: dict, report: Report) -> None:
    """Zotero drops a comment that merely repeats the text it annotates.

    Checking the assembled comment is not enough: the template adds labels such
    as "本可以", which dilute the edit distance until an English field that is
    the quote itself slips under the threshold. Every field is checked too.
    """
    groups = [
        ("claim", [map_dict.get("claim") or {}], "quote", ("text",)),
        ("chain", map_dict.get("chain") or [], "quote", ("text",)),
        ("choices", map_dict.get("choices") or [], "quote", ("choice", "alternative", "solves", "cost")),
        ("figures", map_dict.get("figures") or [], "caption_quote", ("question", "supports", "key_numbers", "caveat")),
        ("limits", map_dict.get("limits") or [], "quote", ("text",)),
        ("pain", map_dict.get("pain") or [], "quote", ("who", "symptom", "cost")),
        ("novelty", map_dict.get("novelty") or [], "quote", ("what", "versus", "why")),
    ]
    for section, items, quote_key, fields in groups:
        for index, item in enumerate(items, 1):
            quote = (item.get(quote_key) or "").strip()
            if not quote:
                continue
            for field in fields + ("note",):
                value = (item.get(field) or "").strip()
                if value and textsim.too_similar(value, quote):
                    report.errors.append(
                        f"{section}[{index}].{field}: repeats the highlighted text; "
                        "Zotero will clear the comment — say what it means instead"
                    )


def _number_errors(map_dict: dict, doc, report: Report) -> None:
    """Every number in the map has to exist in the paper.

    An invented number is the one error a reader cannot catch by reading the
    map: it looks like the paper's own measurement. Tokens are compared after
    comma stripping, so "1,024" and "1024" agree.
    """
    if doc is None:
        return
    text = anchors.normalize(" ".join(page.get_text() for page in doc))
    known = {token.replace(",", "") for token in _NUMBER.findall(text)}
    for section, fields in _NUMBER_FIELDS.items():
        items = map_dict.get(section)
        if not items:
            continue
        rows = [items] if isinstance(items, dict) else list(items)
        for index, item in enumerate(rows, 1):
            if not isinstance(item, dict):
                continue
            for name in fields:
                value = item.get(name)
                if not isinstance(value, str):
                    continue
                for token in _NUMBER.findall(value):
                    cleaned = token.replace(",", "")
                    if cleaned not in known and cleaned not in text:
                        report.errors.append(
                            f"{section}[{index}].{name}: number {token} does not appear "
                            "anywhere in the PDF — never invent numbers"
                        )


def verify(map_dict: dict, doc, density: str = "normal", lang: str = "zh") -> Report:
    report = Report()
    cap = CAPS.get(density, CAPS["normal"])

    # One source of truth for pages: a quote found on another page is corrected
    # here, so the map and the rendered basis cannot disagree.
    if doc is not None:
        fill_pages(map_dict, doc)
        _number_errors(map_dict, doc, report)

    claim = map_dict.get("claim") or {}
    if claim:
        report.highlight_count += 1
        _quote_error(doc, "claim", claim.get("quote", ""), _page(claim), report)

    for index, item in enumerate(map_dict.get("chain") or [], 1):
        report.highlight_count += 1
        _quote_error(doc, f"chain[{index}]", item.get("quote", ""), _page(item), report)

    for index, item in enumerate(map_dict.get("choices") or [], 1):
        report.highlight_count += 1
        label = f"choices[{index}]"
        _quote_error(doc, f"{label}.quote", item.get("quote", ""), _page(item), report)
        if not (item.get("alternative") or "").strip():
            report.errors.append(
                f"{label}: missing alternative — a choice without a "
                "could-have-been is just a description"
            )
        for name in ("alternative", "cost"):
            if item.get(f"{name}_inferred"):
                _inference_error(doc, f"{label}.{name}", item, _page(item), report)

    for index, item in enumerate(map_dict.get("figures") or [], 1):
        if item.get("highlight") is not False:
            report.highlight_count += 1
        label = f"figures[{index}]"
        _quote_error(
            doc, f"{label}.caption_quote", item.get("caption_quote", ""), _page(item), report
        )
        # The numbers a comment quotes often live in the body, not the caption.
        if (item.get("evidence_quote") or "").strip():
            _quote_error(
                doc,
                f"{label}.evidence_quote",
                item["evidence_quote"],
                _page(item),
                report,
                tolerance=doc.page_count,
            )

    for index, item in enumerate(map_dict.get("limits") or [], 1):
        report.highlight_count += 1
        _quote_error(doc, f"limits[{index}]", item.get("quote", ""), _page(item), report)

    # Pain and novelty are map-only — they are our reading of the paper, so
    # they are not highlighted — but a quote they carry is still a quote.
    for section in ("pain", "novelty"):
        for index, item in enumerate(map_dict.get(section) or [], 1):
            if (item.get("quote") or "").strip():
                _quote_error(
                    doc, f"{section}[{index}]", item["quote"], _page(item), report
                )
            else:
                report.errors.append(
                    f"{section}[{index}]: missing quote — say which sentence made you "
                    "think this, or drop the row"
                )
            if section == "novelty":
                origin = (item.get("origin") or "").strip().lower()
                if origin and origin not in ("reused", "adapted", "new"):
                    report.errors.append(
                        f"novelty[{index}]: origin must be reused, adapted or new, "
                        f"not {origin!r}"
                    )
                elif not origin and "borrowed" in item:
                    report.warnings.append(
                        f"novelty[{index}]: the old borrowed flag cannot tell a "
                        "reused component from an adapted one — write origin: "
                        "reused | adapted | new"
                    )

    for index, item in enumerate(map_dict.get("concepts") or [], 1):
        if _basis_of(item):
            _quote_error(
                doc,
                f"concepts[{index}].basis_quote",
                item["basis_quote"],
                _page(item, "basis_page") if item.get("basis_page") is not None else _page(item),
                report,
                tolerance=doc.page_count,
            )

    for index, item in enumerate(map_dict.get("strength") or [], 1):
        label = f"strength[{index}]"
        quote = (item.get("quote") or "").strip()
        if item.get("inferred"):
            if quote:
                report.errors.append(
                    f"{label}: inferred entries must not carry a quote — the quote is "
                    "the paper's sentence; put the sentence you inferred from in "
                    "basis_quote"
                )
            _inference_error(doc, label, item, _page(item), report)
        elif not quote:
            report.errors.append(
                f"{label}: no quote — either quote the paper or set inferred: true "
                "with a basis_quote"
            )
        else:
            _quote_error(doc, label, quote, _page(item), report)

    planned = annotate.plan(map_dict, None, lang=lang)

    seen: dict[str, str] = {}
    for item in planned:
        if item.id in seen:
            report.errors.append(
                f"duplicate annotation id {item.id}: {seen[item.id]} and {item.role} — "
                "a second run would skip one of them"
            )
        else:
            seen[item.id] = item.role

    if report.highlight_count > cap:
        report.errors.append(
            f"highlight count {report.highlight_count} exceeds the {density} cap of {cap}"
        )

    # The cap is about the reader's PDF, not about one map: a second map with
    # fresh ids adds its highlights on top of the first.
    existing = annotate.our_keys(doc) if doc is not None else set()
    if existing and len(existing) + len([p for p in planned if p.id not in existing]) > cap:
        report.errors.append(
            f"this PDF already carries {len(existing)} paper-atlas annotations; after "
            f"this run it would hold more than the {cap} cap — drop rows, or use "
            "--density detailed if you mean it"
        )

    # Zotero deletes a comment that is essentially the text it annotates, so a
    # template echoing the quote would come back empty in the reader. Both
    # languages are checked: passing the wrong --lang must not disarm the guard.
    _echo_errors(map_dict, report)
    variants: dict[str, list[str]] = {}
    for name in annotate.LABELS:
        for item in annotate.plan(map_dict, None, lang=name):
            variants.setdefault(item.id, []).append(item.comment)
    for item in planned:
        for comment in variants.get(item.id, [item.comment]):
            if textsim.too_similar(comment, item.quote):
                report.errors.append(
                    f"{item.role} {item.id}: comment repeats the highlighted text; "
                    "Zotero will clear it — say what it means instead"
                )
                break
        if len(item.comment) > MAX_COMMENT:
            report.errors.append(
                f"{item.role} {item.id}: comment is {len(item.comment)} chars; the limit "
                f"is {MAX_COMMENT} — trim the note rather than lose its caveat"
            )

    return report
