"""Render map.json as the Markdown map a person actually reads."""

from __future__ import annotations

import json
import re
from pathlib import Path

HEADINGS = {
    "zh": {
        "claim": "一句话主张",
        "pain": "痛点",
        "novelty": "创新点",
        "chain": "因果链",
        "choices": "选择点",
        "figures": "图表证据",
        "strength": "证据强度",
        "concepts": "前置概念",
        "terms": "术语表",
        "inferred": "（推断）",
        "columns_choice": "| 选择 | 本可以怎么做 | 解决了什么 | 代价 | 出处 |",
        "columns_novelty": "| 创新 | 相对什么 | 来源 | 凭什么算新 | 出处 |",
        "reused": "原样复用",
        "adapted": "借鉴后改",
        "new": "新造",
        "pain_cost": "代价是{cost}",
        "colon": "：",
        "limits": "存疑",
        "basis": "推断依据",
        "evidence": "数字出处",
        "columns_figure": "| 图表 | 它回答什么 | 支撑 | 关键数字 | 没证明什么 | 页 |",
        "unmarked": "（没高亮）",
        "terms_header": "| Term | 中文 |",
        "page": "p.{page}",
    },
    "en": {
        "claim": "The Claim",
        "pain": "Why it hurts",
        "novelty": "What is new",
        "chain": "The Chain",
        "choices": "Decision Points",
        "figures": "Evidence Map",
        "strength": "How Strong",
        "concepts": "Prerequisites",
        "terms": "Terms",
        "inferred": " (inferred)",
        "columns_choice": "| Choice | Could have | Solves | Costs | Where |",
        "columns_novelty": "| New | Compared with | Origin | Why it counts | Where |",
        "reused": "Reused",
        "adapted": "Adapted",
        "new": "New",
        "pain_cost": "the cost is {cost}",
        "colon": ": ",
        "limits": "Open questions",
        "basis": "Inference basis",
        "evidence": "Numbers come from",
        "columns_figure": "| Item | Question | Supports | Key numbers | Does not prove | Page |",
        "unmarked": " (no highlight)",
        "terms_header": "| Term | Chinese |",
        "page": "p.{page}",
    },
}


def _page(labels: dict, page) -> str:
    return labels["page"].format(page=int(page or 0) + 1)


def _cell(text: str) -> str:
    return (text or "—").replace("|", "\\|").replace("\n", " ")


def _marked(text: str, inferred: bool, labels: dict) -> str:
    return _cell(text) + (labels["inferred"] if inferred else "")


def _origin(item: dict, labels: dict) -> str:
    """How much of this contribution is borrowed, in one of three states.

    `reused` (the component is the prior work, unchanged), `adapted` (the
    component is borrowed but the change is the contribution), `new`. The
    older boolean could not tell the first two apart.
    """
    stated = (item.get("origin") or "").strip().lower()
    if stated in ("reused", "adapted", "new"):
        return labels[stated]
    if "borrowed" in item:
        return labels["reused"] if item["borrowed"] else labels["new"]
    return labels["new"]


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

    pain = map_dict.get("pain") or []
    if pain:
        lines.append(f"## {labels['pain']}")
        lines.append("")
        for item in pain:
            sentence = (
                f"- **{item.get('who', '')}**{labels['colon']}{item.get('symptom', '')}"
            )
            if item.get("cost"):
                cost = labels["pain_cost"].format(cost=item["cost"])
                if item.get("cost_inferred"):
                    cost += labels["inferred"]
                sentence += "，" + cost
            lines.append(sentence + f"（{_page(labels, item.get('page'))}）")
        lines.append("")

    novelty = map_dict.get("novelty") or []
    if novelty:
        lines.append(f"## {labels['novelty']}")
        lines.append("")
        lines.append(labels["columns_novelty"])
        lines.append("| --- | --- | --- | --- | --- |")
        for item in novelty:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _cell(item.get("what", "")),
                        _cell(item.get("versus", "")),
                        _origin(item, labels),
                        _cell(item.get("why", "")),
                        _page(labels, item.get("page")),
                    ]
                )
                + " |"
            )
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
    if choices:
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
    if figures:
        lines.append(f"## {labels['figures']}")
        lines.append("")
        lines.append(labels["columns_figure"])
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for figure in figures:
            label = figure.get("label", "")
            if figure.get("highlight") is False:
                label = f"{label}{labels['unmarked']}"
            lines.append(
                "| "
                + " | ".join(
                    [
                        _cell(label),
                        _cell(figure.get("question", "")),
                        _cell(figure.get("supports", "")),
                        _cell(figure.get("key_numbers", "")),
                        _cell(figure.get("caveat", "")),
                        _page(labels, figure.get("page")),
                    ]
                )
                + " |"
            )
        evidence = [
            (figure.get("label", ""), figure["evidence_quote"])
            for figure in figures
            if (figure.get("evidence_quote") or "").strip()
        ]
        if evidence:
            lines.append("")
            lines.append(f"*{labels['evidence']}*")
            lines.append("")
            for label, quote in evidence:
                lines.append(f"- {label} —— “{quote}”")
        lines.append("")

    bases = []
    for choice in choices:
        if choice.get("basis_quote") and (
            choice.get("alternative_inferred") or choice.get("cost_inferred")
        ):
            bases.append(
                (
                    choice.get("choice", ""),
                    choice["basis_quote"],
                    choice.get("basis_page", choice.get("page")),
                )
            )
    for concept in map_dict.get("concepts") or []:
        if concept.get("basis_quote"):
            bases.append(
                (
                    concept.get("term", ""),
                    concept["basis_quote"],
                    concept.get("basis_page", concept.get("page")),
                )
            )
    if bases:
        lines.append(f"*{labels['basis']}*")
        lines.append("")
        for subject, basis, page in bases:
            lines.append(f"- {subject} —— “{basis}”（{_page(labels, page)}）")
        lines.append("")

    strength = map_dict.get("strength") or []
    if strength:
        lines.append(f"## {labels['strength']}")
        lines.append("")
        for item in strength:
            text = item.get("text", "")
            if item.get("inferred"):
                text += labels["inferred"]
            lines.append(f"- {text}  ")
            source = item.get("basis_quote") if item.get("inferred") else item.get("quote")
            page = item.get("basis_page", item.get("page")) if item.get("inferred") else item.get("page")
            if source:
                lines.append(f"  {_page(labels, page)} · “{source}”")
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
    if terms:
        lines.append(f"## {labels['terms']}")
        lines.append("")
        lines.append(labels["terms_header"])
        lines.append("| --- | --- |")
        for term in terms:
            lines.append(f"| {_cell(term.get('en', ''))} | {_cell(term.get('zh', ''))} |")
        lines.append("")

    limits = map_dict.get("limits") or []
    if limits:
        lines.append(f"## {labels['limits']}")
        lines.append("")
        for item in limits:
            lines.append(f"> {item.get('text', '')}  ")
            lines.append(f"> {_page(labels, item.get('page'))} · “{item.get('quote', '')}”")
            lines.append("")

    return "\n".join(lines)


def has_cjk(text: str) -> bool:
    """True when the text still contains Chinese characters."""
    return re.search(r"[\u4e00-\u9fff]", text) is not None


def write(map_dict: dict, out_dir: Path, lang: str = "zh") -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "map.md"
    target.write_text(render(map_dict, lang=lang), encoding="utf-8")
    (out_dir / "map.json").write_text(
        json.dumps(map_dict, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return target
