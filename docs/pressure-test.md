# Pressure test — 2026-10-18

Same paper (`NICE-SLAM`, arXiv 2112.12130), same machine, two fresh agents.

## Setup

- **Baseline**: "summarize the paper at work/nice-slam.pdf", no skill, no schema.
- **Skill**: read `SKILL.md`, follow its workflow, stop before writing annotations.
- The baseline could not import PyMuPDF, so it read the page text this session had already
  extracted (`work/nice-slam/p01..p17.txt`) and verified it against the PDF. That makes it
  a **strong** baseline, not a strawman.

## What the baseline produced

A ~1,600-word summary with page citations and verbatim quotes, a table pairing each design
choice with the authors' stated motive and its cost, an "established vs inferred" section,
and the measured numbers from Table 4/5. Honestly good writing.

What it did not produce:

- anything that survives the conversation — no file the reader can reopen, no `map.json`;
- any link to the paper's own text: the quotes exist in prose, but nothing is anchored, so
  "where does it say that" is still a manual search;
- any artefact in Zotero;
- any question. It never asked whether it should touch anything.

## What the skill run produced

- `map.md` + `map.json` at `work/pressure-skill/out/`, 17 highlights, `verify_quotes.py`
  → `ok`;
- it viewed the two auto crops and rendered five more itself before writing figure claims;
- it ran the dry run, then **stopped** and handed the consent question back to its caller:
  *"17 highlights into work\nice-slam.pdf (+ backup). Colours: … Run annotate.py --apply?"*
  — the PDF's mtime was unchanged.

That is the difference the skill buys: a durable artefact, provenance, and a stop.

## What the run exposed, and what changed

| Finding | Change |
| --- | --- |
| Two duplicate Zotero items; the agent silently picked one | `SKILL.md` now says: list the matches and ask which |
| Only 2 of 9 captions produced a crop; the agent improvised | `SKILL.md` now says: render the missing region yourself, never describe a figure from its caption alone |
| "≤40 characters" is Chinese-calibrated; English notes ran long | Voice rule now reads ~40 Chinese characters / ~15 English words |
| `render.py` printed a hardcoded 中文 column header in English maps | `terms_header` is localised |
| A subagent cannot ask a human; `ask_user_question` was rejected | Consent rule now says: hand the question back to your caller verbatim |
| English map with Chinese examples as the only reference | Language rule already said "follow the user"; the run confirmed `--lang en` is usable end to end |

## Verdict

On prose quality alone the two runs are close — a capable model writes a decent summary
without help. The skill's value is downstream: the same content becomes a file, every
claim carries a page and a quote, inferences are marked, the reader is asked before their
library changes, and the result can be turned into Zotero annotations in one click.
