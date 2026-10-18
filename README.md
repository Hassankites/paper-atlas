# Paper Atlas

A skill for reading computer-science papers properly: it turns one paper into a **map**
you can reopen — the claim, the chain of prior failures, the design choices and what each
one cost, and what every figure and table actually proves — then, only if you say yes,
writes those key sentences into the PDF as highlights and annotations that **Zotero**
imports.

The point is not a summary. It is structure plus provenance: every line points at a
sentence in the paper, and every inference says which sentence it came from.

## Install

```bash
git clone <this repo> ~/.claude/skills/paper-atlas     # Claude Code
# or: ~/.dsh/skills/paper-atlas                       # DeepSeek Harness
# or: ~/.agents/skills/paper-atlas                    # shared location
cd ~/.claude/skills/paper-atlas
python -m pip install -r requirements.txt
python scripts/doctor.py
```

`doctor.py` checks Python ≥ 3.10, PyMuPDF, and your Zotero data directory.

## Use

```bash
python scripts/find_paper.py "nice-slam"          # item + PDF path from Zotero
python scripts/extract.py paper.pdf --out work/slam
```

Then ask your agent: *"build the map for this paper"*. It writes `map.json`, checks every
quote, renders the map, and — before touching anything — asks whether it may write the
annotations.

The map lands at **`~/paper-atlas/<key>-<slug>/map.md`**, with `map.json` beside it.
If your home directory is not writable (common in sandboxed agents), it falls back to
`./paper-atlas/<same name>/`.

To keep the map in your library, drag `map.md` onto the item in Zotero.

## Highlights and annotations, in two steps

1. `annotate.py --apply` writes standard PDF highlights into the file. Reopen the PDF in
   Zotero and they are there — readable, but read-only.
2. In the Zotero reader, **File → Import Annotations** turns them into real Zotero
   annotations: editable, searchable, synced, and usable with *Create Note from
   Annotations*. No API key needed.

The colours are the map's roles: yellow claim, orange causal chain, green decision,
blue evidence, red open question. Twenty highlights by default, thirty with
`--density detailed`.

Nothing is ever written without your consent: the dry run shows the count, the roles and
the exact file that would change.

## What it will not do

- Translate or rewrite the PDF (annotations anchor to the original text layer).
- Write `zotero.sqlite` (the library is read through a read-only snapshot).
- Guess a highlight location; a quote that does not resolve is dropped and reported.
- Read scanned PDFs without a text layer.
- Review a field or chase citations — one CS paper at a time.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `database is locked` | Zotero is running; the skill snapshots the DB, so run the CLI again |
| No highlights in Zotero | Open the annotated copy, not the original; then re-open the reader |
| Highlights look black | Your build reads `/Zotero:Color` as an array — this skill only writes `/C` |
| `find_paper.py` finds nothing | Pass `--data-dir ~/Zotero`, or give the PDF path directly |
| Chinese map looks garbled in a terminal | `set PYTHONIOENCODING=utf-8` (Windows `chcp 65001`) |

## Layout

```
SKILL.md              the skill itself
scripts/              doctor, find_paper, extract, verify_quotes, annotate, render_map
paper_atlas/          the library behind the scripts
reference/            map schema, worked example, troubleshooting
tests/                pytest suite (`python -m pytest`)
```
