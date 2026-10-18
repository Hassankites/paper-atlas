"""Render map.json as the Markdown map a person actually reads."""

from __future__ import annotations

import json
import re
from pathlib import Path

HEADINGS = {
    "zh": {
        "claim": "一句话主张",
        "chain": "因果链",
        "choices": "选择点",
        "figures": "图表证据",
        "strength": "证据强度",
        "concepts": "前置概念",
        "terms": "术语表",
        "inferred": "（推断）",
        "columns_choice": "| 选择 | 本可以怎么做 | 解决了什么 | 代价 | 出处 |",
        "columns_figure": "| 图表 | 它回答什么 | 支撑 | 关键数字 | 没证明什么 | 页 |",
        "page": "p.{page}",
    },
    "en": {
        "claim": "The Claim",
        "chain": "The Chain",
        "choices": "Decision Points",
        "figures": "Evidence Map",
        "strength": "How Strong",
        "concepts": "Prerequisites",
        "terms": "Terms",
        "inferred": " (inferred)",
        "columns_choice": "| Choice | Could have | Solves | Costs | Where |",
        "columns_figure": "| Item | Question | Supports | Key numbers | Does not prove | Page |",
        "page": "p.{page}",
    },
}


def _page(labels: dict, page) -> str:
    return labels["page"].format(page=int(page or 0) + 1)


def _cell(text: str) -> str:
    return (text or "—").replace("|", "\\|").replace("\n", " ")


def _marked(text: str, inferred: bool, labels: dict) -> str:
    return _cell(text) + (labels["inferred"] if inferred else "")


def default_out_dir(map_dict: dict, base: Path | None = None) -> Path:
    paper = map_dict.get("paper") or {}
    key = paper.get("zotero_key") or "paper"
    title = paper.get("title") or "untitled"
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "untitled"
    root = Path(base) if base else Path.home() / "paper-atlas"
    return root / f"{key}-{slug}"


def resolve_out_dir(map_dict: dict, explicit: Path | None = None) -> Path:
    """Default to ~/paper-atlas, but survive a read-only home directory.

    Agent harnesses often sandbox writes; a map that cannot be written is
    worse than a map in the working directory.
    """
    if explicit:
        return Path(explicit)
    candidate = default_out_dir(map_dict)
    try:
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    except OSError:
        fallback = Path.cwd() / "paper-atlas" / candidate.name
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def render(map_dict: dict, lang: str = "zh") -> str:
    labels = HEADINGS.get(lang, HEADINGS["zh"])
    lines: list[str] = []

    title = (map_dict.get("paper") or {}).get("title") or "Map"
    lines.append(f"# {title}")
    lines.append("")

    claim = map_dict.get("claim") or {}
    if claim:
        lines.append(f"## {labels['claim']}")
        lines.append("")
        lines.append(f"> {claim.get('text', '')}")
        lines.append("")
        lines.append(f"{_page(labels, claim.get('page'))} · “{claim.get('quote', '')}”")
        lines.append("")

    chain = map_dict.get("chain") or []
    if chain:
        lines.append(f"## {labels['chain']}")
        lines.append("")
        for index, step in enumerate(chain, 1):
            head = f"**{step.get('step', '')}** " if step.get("step") else ""
            lines.append(f"{index}. {head}{step.get('text', '')}  ")
            lines.append(f"   {_page(labels, step.get('page'))} · “{step.get('quote', '')}”")
        lines.append("")

    choices = map_dict.get("choices") or []
    lines.append(f"## {labels['choices']}")
    lines.append("")
    lines.append(labels["columns_choice"])
    lines.append("| --- | --- | --- | --- | --- |")
    for choice in choices:
        lines.append(
            "| "
            + " | ".join(
                [
                    _cell(choice.get("choice", "")),
                    _marked(
                        choice.get("alternative", ""),
                        bool(choice.get("alternative_inferred")),
                        labels,
                    ),
                    _cell(choice.get("solves", "")),
                    _marked(
                        choice.get("cost", ""), bool(choice.get("cost_inferred")), labels
                    ),
                    _page(labels, choice.get("page")),
                ]
            )
            + " |"
        )
    lines.append("")

    figures = map_dict.get("figures") or []
    lines.append(f"## {labels['figures']}")
    lines.append("")
    lines.append(labels["columns_figure"])
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for figure in figures:
        lines.append(
            "| "
            + " | ".join(
                [
                    _cell(figure.get("label", "")),
                    _cell(figure.get("question", "")),
                    _cell(figure.get("supports", "")),
                    _cell(figure.get("key_numbers", "")),
                    _cell(figure.get("caveat", "")),
                    _page(labels, figure.get("page")),
                ]
            )
            + " |"
        )
    lines.append("")

    strength = map_dict.get("strength") or []
    if strength:
        lines.append(f"## {labels['strength']}")
        lines.append("")
        for item in strength:
            lines.append(f"- {item.get('text', '')}  ")
            lines.append(f"  {_page(labels, item.get('page'))} · “{item.get('quote', '')}”")
        lines.append("")

    concepts = map_dict.get("concepts") or []
    if concepts:
        lines.append(f"## {labels['concepts']}")
        lines.append("")
        for concept in concepts:
            lines.append(
                f"- **{concept.get('term', '')}** — {concept.get('gloss', '')} "
                f"({_page(labels, concept.get('page'))})"
            )
        lines.append("")

    terms = map_dict.get("terms") or []
    lines.append(f"## {labels['terms']}")
    lines.append("")
    if terms:
        lines.append("| Term | 中文 |")
        lines.append("| --- | --- |")
        for term in terms:
            lines.append(f"| {_cell(term.get('en', ''))} | {_cell(term.get('zh', ''))} |")
    lines.append("")

    limits = map_dict.get("limits") or []
    if limits:
        lines.append("---")
        lines.append("")
        for item in limits:
            lines.append(f"> {item.get('text', '')}  ")
            lines.append(f"> {_page(labels, item.get('page'))} · “{item.get('quote', '')}”")
            lines.append("")

    return "\n".join(lines)


def write(map_dict: dict, out_dir: Path, lang: str = "zh") -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "map.md"
    target.write_text(render(map_dict, lang=lang), encoding="utf-8")
    (out_dir / "map.json").write_text(
        json.dumps(map_dict, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return target
