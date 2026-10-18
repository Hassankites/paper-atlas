"""Check a map before a single annotation is written.

Two things are refused outright: a quote that is not in the paper, and an
inference that does not say which sentence it came from. A third is
refused softly: more highlights than the density cap allows.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from paper_atlas import anchors, annotate, textsim

CAPS = {"normal": 20, "detailed": 30}


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    highlight_count: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def _quote_error(
    doc, label: str, quote: str, page: int, report: Report, tolerance: int = 1
) -> None:
    if not quote or not quote.strip():
        report.errors.append(f"{label}: missing quote")
        return
    found = anchors.locate(doc, page, quote, tolerance_pages=tolerance)
    if found is None:
        report.errors.append(f"{label}: quote not found: {quote[:60]!r}")
        return
    page_index, _ = found
    occurrences = anchors.count_occurrences(doc[page_index], quote)
    if occurrences > 1:
        report.errors.append(
            f"{label}: quote occurs {occurrences} times on p.{page_index + 1}; "
            "lengthen it until it is unique"
        )


def _inference_error(doc, label: str, entry: dict, page: int, report: Report) -> None:
    basis = (entry.get("basis_quote") or "").strip()
    if not basis:
        report.errors.append(f"{label}: inferred without basis_quote")
        return
    # The sentence an inference rests on may sit anywhere in the paper.
    _quote_error(
        doc, f"{label}.basis_quote", basis, page, report, tolerance=doc.page_count
    )


def verify(map_dict: dict, doc, density: str = "normal") -> Report:
    report = Report()
    cap = CAPS.get(density, CAPS["normal"])

    claim = map_dict.get("claim") or {}
    if claim:
        report.highlight_count += 1
        _quote_error(doc, "claim", claim.get("quote", ""), claim.get("page", 0), report)

    for index, item in enumerate(map_dict.get("chain") or [], 1):
        report.highlight_count += 1
        _quote_error(
            doc, f"chain[{index}]", item.get("quote", ""), item.get("page", 0), report
        )

    for index, item in enumerate(map_dict.get("choices") or [], 1):
        report.highlight_count += 1
        page = item.get("page", 0)
        _quote_error(doc, f"choices[{index}].quote", item.get("quote", ""), page, report)
        if not (item.get("alternative") or "").strip():
            report.errors.append(
                f"choices[{index}]: missing alternative — a choice without a "
                "could-have-been is just a description"
            )
        for name in ("alternative", "cost"):
            if item.get(f"{name}_inferred"):
                _inference_error(doc, f"choices[{index}].{name}", item, page, report)

    for index, item in enumerate(map_dict.get("figures") or [], 1):
        report.highlight_count += 1
        _quote_error(
            doc,
            f"figures[{index}].caption_quote",
            item.get("caption_quote", ""),
            item.get("page", 0),
            report,
        )

    for index, item in enumerate(map_dict.get("limits") or [], 1):
        report.highlight_count += 1
        _quote_error(
            doc, f"limits[{index}]", item.get("quote", ""), item.get("page", 0), report
        )

    for index, item in enumerate(map_dict.get("strength") or [], 1):
        page = item.get("page", 0)
        if item.get("inferred"):
            _inference_error(doc, f"strength[{index}]", item, page, report)
        else:
            _quote_error(doc, f"strength[{index}]", item.get("quote", ""), page, report)

    if report.highlight_count > cap:
        report.errors.append(
            f"highlight count {report.highlight_count} exceeds the {density} cap of {cap}"
        )

    # Zotero deletes a comment that is essentially the text it annotates, so a
    # template echoing the quote would come back empty in the reader.
    for item in annotate.plan(map_dict, None):
        if textsim.too_similar(item.comment, item.quote):
            report.errors.append(
                f"{item.role} {item.id}: comment repeats the highlighted text; "
                "Zotero will clear it — say what it means instead"
            )

    return report
