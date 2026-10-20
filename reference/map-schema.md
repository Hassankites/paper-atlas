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
the highlight budget stays for sentences in the paper. Their `quote` is required and is
checked by the verifier: a pain you cannot point at is usually a property, not a pain.

`paper.zotero_key` becomes part of every annotation id (`pa-<key>-<entry>`), which is
what makes a second run skip instead of duplicating. Two entries may not share an id —
the verifier rejects a duplicate, because the PDF would get two marks with one key.

## Entry fields

**Highlighted** (the quote must be verbatim in the PDF):

| Field | Where | Meaning |
| --- | --- | --- |
| `quote` | claim, chain, choices, limits | the sentence to highlight |
| `caption_quote` | figures | the caption sentence to highlight |
| `evidence_quote` | figures (optional) | the sentence or table row a cited number comes from; verified, not highlighted |
| `page` | all | 0-based page index where the quote lives |

**Judgement** (may be inference):

| Field | Meaning |
| --- | --- |
| `text` / `choice` | your one-line statement |
| `alternative` + `alternative_inferred` | what else could have been done |
| `solves` | what the choice buys |
| `cost` + `cost_inferred` | what it gives up |
| `basis_quote` | the sentence an inference rests on — required whenever `*_inferred` is true; may live on any page |
| `basis_page` | optional; the verifier fills the real page in when it differs |
| `note` | the annotation text, written in the Voice of `SKILL.md`. Wins over the template |

**Pain and novelty** (map-only):

| Field | Where | Meaning |
| --- | --- | --- |
| `who`, `symptom`, `cost` | pain | who feels it, what they see, what it costs them |
| `cost_inferred` | pain | `cost` was not written down; marked 「（推断）」 in the map |
| `what` | novelty | the claimed contribution, in one line |
| `versus` | novelty | the prior work or line of work it is new relative to |
| `origin` | novelty | `reused` (原样复用), `adapted` (借鉴后改), `new` (新造) |
| `why` | novelty | why this counts as new, or why the borrowing is honest |

`origin` replaces the old boolean `borrowed`; a map still using it verifies with a
warning and renders the old way.

**Strength** (map-only, never highlighted):

| Field | Meaning |
| --- | --- |
| `text` | how much the evidence carries |
| `inferred` | `true` when you drew the conclusion yourself — then `quote` must be absent |
| `basis_quote` | required when `inferred` is true, and shown under the section |
| `quote` | a sentence the authors use to hedge, when it exists |

**Figures:**

| Field | Meaning |
| --- | --- |
| `label` | `Figure 3` / `Table 5` (Chinese captions are normalised to this) |
| `question` | what question this figure answers |
| `supports` | which part of the argument it props up — in words, never an id |
| `key_numbers` | the numbers it carries, copied from the table |
| `caveat` | what it does **not** prove |
| `highlight` | `false` keeps the figure in the map without a blue mark |

## Rules the checker enforces

- Every highlighted field resolves in the PDF; a missing quote is an error, not a warning.
- A quote that occurs more than once on a page is ambiguous; make it longer.
- Every `*_inferred: true` carries a `basis_quote` that resolves anywhere in the paper.
- Every annotation id is unique.
- A comment stays under 240 characters; the checker asks you to rewrite it rather than
  truncating, because the caveat sits last.
- Highlight count (claim + chain + choices + highlighted figures + limits) stays under
  the density cap: 20 normal, 30 detailed — counted against the annotations the PDF
  already carries, so a second map on the same file cannot double the page load.

## Minimal example

```json
{
  "paper": {"title": "NICE-SLAM", "zotero_key": "NICESLAM"},
  "claim": {
    "text": "多层网格替换单个 MLP，用于大场景重建",
    "quote": "we present NICE-SLAM, a dense SLAM system that incorporates multi-level local information",
    "page": 0,
    "note": "把单个 MLP 换成多层网格，局部更新只改一层。"
  },
  "pain": [
    {
      "who": "用平板扫整套房子的用户",
      "symptom": "换房间后重建变糊，追踪也变差",
      "cost": "得重扫",
      "quote": "significant performance drops are observed in both the dense reconstruction and camera tracking",
      "page": 3
    }
  ],
  "novelty": [
    {
      "what": "分层特征网格",
      "versus": "iMAP 的单个 MLP",
      "origin": "new",
      "why": "网格可以局部更新，MLP 只能整体更新",
      "quote": "a hierarchical scene representation",
      "page": 1
    }
  ],
  "choices": [
    {
      "id": "d1",
      "choice": "粗层用 2m 分辨率",
      "quote": "we use a very low resolution, with a side-length of 2m",
      "page": 2,
      "alternative": "只用一个高分辨率网格",
      "alternative_inferred": true,
      "basis_quote": "one feature grid with the same resolution as our fine-level representation",
      "solves": "未观测区域可以先填上",
      "cost": "细节要靠中、细层补"
    }
  ]
}
```
