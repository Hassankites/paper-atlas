---
name: paper-atlas
description: Use when someone wants to understand a computer-science paper's skeleton - what it claims, why prior work failed, which choices the authors made and what each cost, and what every figure and table actually proves - and wants that written back into Zotero as highlights and annotations. Triggers on "summarize this paper", "理清这篇论文的脉络", "这篇论文的图表分别在证明什么", "帮我在 Zotero 里做批注".
---

# Paper Atlas

Turn one paper into a **map** you can reopen, and — only if the user says yes — into
highlights and annotations inside the PDF that Zotero imports.

The value is not a summary. It is **structure plus provenance**: every line points
back to a sentence in the paper, and every inference says which sentence it came from.

## Hard rules

1. **Never translate, re-flow, or rewrite the PDF.** No translated copy, no text-layer
   edits. Everything anchors to the original file.
2. **Every highlight is a verbatim quote.** If a sentence cannot be located in the PDF,
   drop it and say so; never guess a location.
3. **Inference is allowed, hiding it is not.** `alternative`, `cost`, and `strength`
   are usually not written down by the authors. Mark them `*_inferred: true`, attach a
   `basis_quote`, and never highlight them.
4. **Ask before writing annotations.** Run the dry run, show the count, the colours and
   the exact file that would change, then wait for an explicit yes. No yes, no `--apply`.
   Many readers do not want their library touched; the map alone is a complete answer.
   If you cannot reach a human (you are a subagent), stop and hand the consent question
   back to your caller verbatim — do not decide for them.
5. **20 highlights by default**, 30 with `--density detailed`. A page of highlighter is
   worse than none.
6. **Never write `zotero.sqlite`.** `find_paper.py` reads a snapshot; the live database
   is off-limits.
7. **Never invent numbers.** Every number in the map comes from the text or a table.

## Workflow

```bash
python scripts/doctor.py
python scripts/find_paper.py "nice-slam"
python scripts/extract.py <paper.pdf> --out work/<slug>/
```

**If several items match**, list them (title + key + PDF path) and ask which one. Two
copies of the same paper are common; picking silently writes annotations into the wrong
item.

Then, in your own words: read `work/<slug>/structure.json`, and **look at the crops**
under `work/<slug>/figs/` with your image tool before saying what a figure shows.
Extraction often crops only a couple of figures; when a caption has no crop, render that
region yourself and look at it — never describe a figure you have only seen the caption of.
Write `map.json` (schema: `reference/map-schema.md`), then:

```bash
python scripts/verify_quotes.py map.json --pdf <paper.pdf>
python scripts/render_map.py map.json            # writes the Markdown map
python scripts/annotate.py map.json --pdf <paper.pdf>          # dry run
python scripts/annotate.py map.json --pdf <paper.pdf> --apply  # only after consent
```

Tell the user where the map landed, and that Zotero's reader has **File → Import
Annotations** if they want the highlights to become editable, syncable annotations.

### Where the map appears

`~/paper-atlas/<zotero key>-<title slug>/map.md` (plus `map.json` beside it).
If the home directory is not writable, it falls back to `./paper-atlas/<same name>/`.
Always print the final path. To keep it in the library, drag `map.md` onto the item in
Zotero — it becomes an attachment next to the PDF.

## Voice

Annotations are read while someone is mid-paper, so they must sound like a labmate
leaning over, not a report generator.

- One idea per note. ~40 characters in Chinese, or ~15 words in English. Short
  sentences. Concrete nouns.
- Say the judgement, not the process: 「粗层故意做糙，专门管没看见的地方」 beats
  「本方法采用了低分辨率粗层以处理未观测区域」.
- Banned: 旨在、从而实现、赋能、有效提升、进一步、综上所述；三段式口号
  （「本可以…｜解决…｜代价…」）当万能句式；连着三个四字词。
- No bullet labels inside a note. If you need all three of alternative / solves / cost
  for a choice, the map table already has them — the note can pick the one thing that
  matters.
- The template in `annotate.py` is a fallback for entries without a `note`. When you
  care about the wording, write the `note` yourself.
- English output follows the same rule: "the coarse grid is deliberately blurry, and
  that is what makes unseen rooms tractable", not "a low-resolution coarse level is
  employed to handle unobserved regions".

## The map

Eight sections: claim / **why it hurts** / **what is new** / causal chain / decision points /
evidence map / how strong / prerequisites + terms.

Two of them carry the weight, because a good summary already does the rest:

- **痛点 / Why it hurts** — name who feels it, what the symptom is, and what it costs them
  (a rescan, a manual cleanup, a room-sized limit). "Prior methods are not scalable" is not
  a pain; "you can only scan one room, so a flat means starting over" is.
- **创新点 / What is new** — one row per claimed contribution, compared against a *named*
  prior work, with an honest **borrowed vs built** column. Most papers borrow most of their
  stack (a decoder, a renderer, a loss); saying which parts are new is the point. If every
  row is "built", you probably have not read the related work closely enough.

The decision table's **"could have been"** column is the other thing a summary never has —
without it a decision is just a description.

## Failure handling

| Situation | Do this |
| --- | --- |
| No Zotero library, or item not found | Ask for the PDF path; do not guess |
| PDF has no text layer | Stop; say scanned PDFs are out of scope |
| Caption not detected | Read the page text, add the figure entry by hand, mark `detected: manual` |
| `verify_quotes.py` fails | Fix the quote, never the check |
| User declines annotations | Ship the map only; that is a valid finish |
| Zotero shows nothing after `--apply` | Check it is a *copy* opened in Zotero, then re-open; then File → Import Annotations |

## Language

Follow the user: Chinese request → Chinese map and notes, English terms kept in
parentheses; English request → English throughout. `--lang en` forces English.

## What this is not

Not a literature review, not a citation chaser, not an OCR pipeline, not a Zotero
plugin. One paper at a time, CS first.
