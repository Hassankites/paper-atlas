# map.json

One file per paper. The agent writes it; `verify_quotes.py` checks it; `annotate.py`
turns it into highlights; `render_map.py` turns it into `map.md`.

## Top level

```json
{
  "paper": {"title": "…", "arxiv": "…", "zotero_key": "ABCD1234", "pdf": "…"},
  "claim": {...},
  "pain": [...],
  "novelty": [...],
  "chain": [...],
  "choices": [...],
  "figures": [...],
  "strength": [...],
  "concepts": [...],
  "limits": [...],
  "terms": [...]
}
```

`pain` and `novelty` are **not highlighted** — they are the map's analytical layer, and
the highlight budget stays for sentences in the paper. They carry an optional `quote`
checked by the verifier.

`paper.zotero_key` becomes part of every annotation id (`pa-<key>-<entry>`), which is
what makes a second run skip instead of duplicating.

## Entry fields

**Highlighted** (the quote must be verbatim in the PDF):

| Field | Where | Meaning |
| --- | --- | --- |
| `quote` | claim, chain, choices, limits, strength | the sentence to highlight |
| `caption_quote` | figures | the caption sentence to highlight |
| `page` | all | 0-based page index where the quote lives |

**Judgement** (may be inference):

| Field | Meaning |
| --- | --- |
| `text` / `choice` | your one-line statement |
| `alternative` + `alternative_inferred` | what else could have been done |
| `solves` | what the choice buys |
| `cost` + `cost_inferred` | what it gives up |
| `basis_quote` | the sentence an inference rests on — required whenever `*_inferred` is true; may live on any page |
| `note` | the annotation text, written in the Voice of `SKILL.md`. Wins over the template |

**Pain and novelty** (map-only):

| Field | Where | Meaning |
| --- | --- | --- |
| `who`, `symptom`, `cost` | pain | who feels it, what they see, what it costs them |
| `what` | novelty | the claimed contribution, in one line |
| `versus` | novelty | the named prior work it is new relative to |
| `borrowed` | novelty | `true` when the paper reuses an existing component unchanged |
| `why` | novelty | why this counts as new (or why the borrowing is honest) |

**Figures:**

| Field | Meaning |
| --- | --- |
| `label` | `Figure 3` / `Table 5` (Chinese captions are normalised to this) |
| `question` | what question this figure answers |
| `supports` | which part of the argument it props up — in words, never an id |
| `key_numbers` | the numbers it carries, copied from the table |
| `caveat` | what it does **not** prove |

## Rules the checker enforces

- Every highlighted field resolves in the PDF; a missing quote is an error, not a warning.
- Every `*_inferred: true` carries a `basis_quote` that resolves anywhere in the paper.
- Highlight count (claim + chain + choices + figures + limits) stays under the density
  cap: 20 normal, 30 detailed.

## Minimal example

```json
{
  "paper": {"title": "NICE-SLAM", "zotero_key": "NICESLAM"},
  "claim": {
    "text": "分层网格 + 冻结解码器才撑得住大场景",
    "quote": "we present NICE-SLAM, a dense SLAM system that incorporates multi-level local information",
    "page": 0,
    "note": "整篇一句话：一个 MLP 撑不住，换成多层网格。"
  },
  "choices": [
    {
      "id": "d1",
      "choice": "粗层故意做糙（2m）",
      "quote": "we use a very low resolution, with a side-length of 2m",
      "page": 2,
      "alternative": "只用一个高分辨率网格",
      "alternative_inferred": true,
      "basis_quote": "one feature grid with the same resolution as our fine-level representation",
      "solves": "没观测到的地方也能外推",
      "cost": "细节全靠中/细层"
    }
  ]
}
```
