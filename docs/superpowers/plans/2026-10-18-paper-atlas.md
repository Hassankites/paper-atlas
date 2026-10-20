# Paper Atlas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a distributable `paper-atlas` skill that turns one CS paper's PDF (located through Zotero) into a bilingual map plus highlights and annotations that Zotero displays and can promote to real, editable annotations.

**Architecture:** A Python package `paper_atlas/` (PyMuPDF + stdlib `sqlite3`) holds pure, testable functions; thin `scripts/*.py` CLIs wrap them; `SKILL.md` drives the agent through locate → extract → read figure crops → draft `map.json` → verify → annotate → one-click import in Zotero. No network at runtime.

**Tech Stack:** Python 3.10+, PyMuPDF, pytest, stdlib `sqlite3`; no network calls in shipped code.

**Spec:** `docs/superpowers/specs/2026-10-17-paper-atlas-design.md`

## Global Constraints

- Zotero's database is opened read-only via `sqlite3.connect("file:<path>?mode=ro", uri=True)`; the skill never writes `zotero.sqlite`.
- Never create or modify a translated PDF; never rewrite a PDF's text layer.
- Every highlighted field is a verbatim quote from the paper. Inferred fields carry `basis_quote` and are never highlighted.
- Default cap is 20 highlights per paper; `--density detailed` raises it to 30.
- Never guess coordinates. A quote that cannot be located is skipped and reported.
- Always write `<name>.paper-atlas.bak.pdf` before modifying a PDF.
- Re-running `annotate.py` on the same map adds zero new annotations.
- `find_paper.py` and `doctor.py` must work on Windows, macOS and Linux, under non-ASCII paths (this machine: a non-ASCII profile path).
- User-facing copy ships in English and 简体中文 (`README.md`, `README.zh-CN.md`, bilingual map headings).
- Annotation comments must never equal the highlighted text (Zotero clears those).

## Review Focus

1. **Two-column text with hyphenation.** Quote search must stitch `recon-\nstruction` and must not match the same word in the other column. Owned by Task 5 (anchors).
2. **Non-ASCII Zotero data dir.** Every path goes through `pathlib` and is passed as a `Path`, never a shell string. Owned by Tasks 1 and 3.
3. **Re-running on an already-annotated PDF.** Must add zero duplicates, not rewrite the backup, not corrupt existing annotations. Owned by Task 7 (annotate).
4. **Caption separated from its figure, or a table with no image.** Figure rendering degrades to caption-only without crashing. Owned by Task 4 (extract).
5. **Comment ≈ highlighted text.** Zotero silently clears such comments; the annotator must guarantee a difference. Owned by Task 7.

---

### Task 1: Package skeleton, bootstrap, doctor

**Files:**
- Create: `.gitignore`, `requirements.txt`, `paper_atlas/__init__.py`, `paper_atlas/doctor.py`, `scripts/doctor.py`, `scripts/bootstrap.py`, `tests/test_doctor.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `paper_atlas.doctor.check() -> dict` with keys `"python"` (str), `"pymupdf"` (str | None), `"zotero_data"` (str | None), `"problems"` (list[str]); `paper_atlas.doctor.main(argv: list[str] | None = None) -> int`.

- [ ] **Step 1: Scaffold the repo**

```bash
git init
```

`.gitignore`: `__pycache__/`, `.pytest_cache/`, `.venv/`, `work/`, `*.paper-atlas.bak.pdf`.

`requirements.txt`:

```
pymupdf>=1.24
pytest>=8
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_doctor.py
from paper_atlas import doctor


def test_check_reports_environment_keys():
    report = doctor.check()
    assert set(report) == {"python", "pymupdf", "zotero_data", "problems"}
    assert report["python"].startswith("3.")
    assert isinstance(report["problems"], list)


def test_main_fails_when_a_problem_exists(monkeypatch):
    monkeypatch.setattr(doctor, "check", lambda: {
        "python": "3.12.10", "pymupdf": None, "zotero_data": None,
        "problems": ["missing: pymupdf"],
    })
    assert doctor.main([]) == 1
```

- [ ] **Step 3: Run it and confirm it fails**

Run: `python -m pytest tests/test_doctor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'paper_atlas'`.

- [ ] **Step 4: Implement `paper_atlas/doctor.py` and `paper_atlas/__init__.py`**

`check()` returns the four keys; `pymupdf` is `importlib.metadata.version("pymupdf")` wrapped in `try/except ImportError`; `zotero_data` is `str(paper_atlas.zotero.default_data_dir())` when that directory exists, else `None`; every missing item appends one line to `problems`. `main()` prints the report and returns `0 if not problems else 1`.

`scripts/doctor.py` is a four-line wrapper that puts the repo root on `sys.path` and calls `paper_atlas.doctor.main()`.

`scripts/bootstrap.py` creates `.venv` in the repo root, installs `requirements.txt` with that interpreter, and prints the interpreter path.

- [ ] **Step 5: Run the test, then commit**

Run: `python -m pytest tests/test_doctor.py -v`
Expected: PASS.

```bash
git add -A && git commit -m "chore: scaffold paper-atlas package, bootstrap and doctor"
```

---

### Task 2: M0 probe — does Zotero show externally written annotations?

This task is the load-bearing gate. If it fails, stop and use the spec's §10 fallback ladder instead of building Tasks 3–7.

**Files:**
- Create: `scripts/probe_annotations.py`, `tests/test_probe.py`, `docs/superpowers/specs/m0-result.md`

**Interfaces:**
- Consumes: `paper_atlas.doctor` (for the data dir).
- Produces: `probe.write_probe(pdf_path: Path, out_path: Path) -> list[str]` returning the generated keys; CLI flags `--out PATH` and `--check-db`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_probe.py
import fitz
from scripts.probe_annotations import write_probe


def test_probe_writes_zotero_readable_highlights(tmp_path):
    pdf = tmp_path / "in.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "The quick brown fox jumps over the lazy dog.", fontsize=12)
    doc.save(pdf)

    keys = write_probe(pdf, tmp_path / "out.pdf")
    assert len(keys) == 2

    out = fitz.open(tmp_path / "out.pdf")
    annots = [a for a in out[0].annots() if a.type[1] == "Highlight"]
    assert len(annots) == 2
    for annot, key in zip(annots, keys):
        info = annot.info
        assert info["content"], "comment must not be empty"
        assert info["content"] != annot.get_text().strip()
        assert annot.parent.get_keys()  # /Zotero:AuthorName present via xref dict
```

Assert the Zotero keys through `doc.xref_get_key(annot.xref, "Zotero:AuthorName") == ("string", "Paper Atlas")` and `... "Zotero:Key"` starts with `pa-probe-`.

- [ ] **Step 2: Run it and confirm it fails**

Run: `python -m pytest tests/test_probe.py -v`
Expected: FAIL — `ModuleNotFoundError: scripts.probe_annotations`.

- [ ] **Step 3: Implement the probe**

`write_probe` opens the PDF, adds two highlight annotations on the sentence (`add_highlight_annot(quads)`), sets `/Contents` to a written comment that differs from the quote, sets `/Zotero:AuthorName`, `/Zotero:Color`, `/Zotero:Key` via `xref_set_key`, saves `out_path`, returns the keys. `--check-db` opens `zotero.sqlite` read-only and prints `select count(*) from itemAnnotations where isExternal=1`.

- [ ] **Step 4: Run the test**

Run: `python -m pytest tests/test_probe.py -v`
Expected: PASS.

- [ ] **Step 5: Run the human gate**

```bash
python scripts/probe_annotations.py "<any-paper.pdf>" --out work/probe.pdf
```

Ask the user to drag `work/probe.pdf` into Zotero, open it in the reader, and say whether two yellow highlights with visible comments appear. Then run `--check-db` and confirm a non-zero count. Record the outcome, the Zotero version and any deviation (color, author, comment) in `docs/superpowers/specs/m0-result.md`.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: probe Zotero import of externally written annotations"
```

---

### Task 3: Locate the paper in Zotero

**Files:**
- Create: `paper_atlas/zotero.py`, `scripts/find_paper.py`, `tests/test_zotero.py`, `tests/fixtures/build_zotero_fixture.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `@dataclass(frozen=True) class PaperHit: item_id: int; key: str; title: str; pdf_path: Path | None`
  - `default_data_dir() -> Path`
  - `connect_ro(data_dir: Path) -> sqlite3.Connection`
  - `find_item(conn, query: str, limit: int = 5) -> list[PaperHit]`
  - `resolve_pdf(conn, item_id: int, data_dir: Path) -> Path | None`

- [ ] **Step 1: Write the fixture builder and failing tests**

`build_zotero_fixture.py` creates a SQLite file with the real subset of Zotero's schema: `items(itemID, itemTypeID, libraryID, key)`, `itemData(itemID, fieldID, valueID)`, `itemDataValues(valueID, value)`, `fields(fieldID, fieldName)`, `itemAttachments(itemID, parentItemID, path, contentType)`, plus a `storage/<KEY>/<file>.pdf` tree under a `tmp_path`. Seed one item titled `NICE-SLAM: Neural Implicit Scalable Encoding for SLAM` with a `storage:` attachment and a Chinese-named user directory.

```python
def test_find_item_matches_title_case_insensitively(fixture):
    conn = zotero.connect_ro(fixture.data_dir)
    hits = zotero.find_item(conn, "nice-slam")
    assert len(hits) == 1
    assert hits[0].title.startswith("NICE-SLAM")


def test_resolve_pdf_returns_existing_path(fixture):
    conn = zotero.connect_ro(fixture.data_dir)
    hit = zotero.find_item(conn, "NICE-SLAM")[0]
    assert hit.pdf_path is not None and hit.pdf_path.exists()


def test_resolve_pdf_returns_none_when_file_missing(fixture):
    fixture.remove_pdf()
    conn = zotero.connect_ro(fixture.data_dir)
    assert zotero.resolve_pdf(conn, 1, fixture.data_dir) is None


def test_connect_ro_cannot_write(fixture):
    conn = zotero.connect_ro(fixture.data_dir)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("insert into items (itemID) values (99)")
```

- [ ] **Step 2: Run and confirm failure**

Run: `python -m pytest tests/test_zotero.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `paper_atlas/zotero.py`**

`default_data_dir()` checks `$ZOTERO_DATA`, then `~/Zotero` (and the macOS/Linux equivalents), returning the first directory containing `zotero.sqlite`. `find_item` joins `items` → `itemData` → `itemDataValues` → `fields` where `fieldName='title'` and `lower(value) like '%'||lower(?)||'%'`, and attaches `resolve_pdf`. `resolve_pdf` takes the single PDF attachment (`contentType='application/pdf'`), strips the `storage:` prefix and resolves against `data_dir/storage/<key>/`.

`scripts/find_paper.py` prints one line per hit: `item_id`, key, title, resolved path, or an explicit `PDF not attached` line.

- [ ] **Step 4: Run the tests**

Run: `python -m pytest tests/test_zotero.py -v`
Expected: PASS (four tests).

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: locate a paper and its PDF in the Zotero library"
```

---

### Task 4: Extract structure and figure crops

**Files:**
- Create: `paper_atlas/extract.py`, `scripts/extract.py`, `tests/test_extract.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `extract_structure(pdf_path: Path) -> dict` with `{"pages": [{"index", "width", "height", "blocks": [{"bbox", "text", "size"}]}], "sections": [{"title", "page"}], "figures": [{"label", "page", "caption", "bbox"}]}`
  - `render_figures(structure: dict, pdf_path: Path, out_dir: Path, dpi: int = 160) -> list[dict]` adding `"crop"` (str path) or `"crop": None` when no image can be located.

- [ ] **Step 1: Write the failing tests**

Build a two-page fixture with `fitz`: page 1 with a 18pt title, 10pt body, a heading `1 Introduction` at 12pt; page 2 with a drawn shape, caption `Figure 1: Reconstruction quality on Replica.` at 9pt, and caption `Table 2: Tracking results.` with no image.

```python
def test_detects_sections_and_figures(fixture_pdf):
    s = extract.extract_structure(fixture_pdf)
    assert any(sec["title"].startswith("1 Introduction") for sec in s["sections"])
    labels = [f["label"] for f in s["figures"]]
    assert "Figure 1" in labels and "Table 2" in labels


def test_figure_without_image_degrades_to_caption_only(fixture_pdf, tmp_path):
    s = extract.extract_structure(fixture_pdf)
    crops = extract.render_figures(s, fixture_pdf, tmp_path)
    table = next(c for c in crops if c["label"] == "Table 2")
    assert table["crop"] is None


def test_crop_file_is_created_and_non_empty(fixture_pdf, tmp_path):
    s = extract.extract_structure(fixture_pdf)
    crops = extract.render_figures(s, fixture_pdf, tmp_path)
    fig = next(c for c in crops if c["label"] == "Figure 1")
    assert fig["crop"] and Path(fig["crop"]).stat().st_size > 1000
```

- [ ] **Step 2: Run and confirm failure**, then implement.

`extract_structure` uses `page.get_text("dict")` blocks with `spans`; body size is the mode of span sizes; a section is a block whose max span size ≥ body × 1.15 or matching `^\d+(\.\d+)*\s+\S`. A figure is a block whose text matches `^(Figure|Fig\.|Table)\s*\d+\s*[:.]`. `render_figures` clips the region between the previous text block and the caption when one exists; otherwise it falls back to the caption band only, and returns `crop: None` for tables with no drawn content.

- [ ] **Step 3: Run the tests** — `python -m pytest tests/test_extract.py -v` → PASS.

- [ ] **Step 4: Commit** — `git commit -m "feat: extract page structure, sections, captions and figure crops"`.

---

### Task 5: Anchor quotes to rectangles

**Files:**
- Create: `paper_atlas/anchors.py`, `tests/test_anchor_fixture.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `normalize(text: str) -> str`; `find_rects(page, quote: str) -> list[fitz.Rect]`; `locate(doc, page_index: int, quote: str, tolerance_pages: int = 1) -> tuple[int, list[fitz.Rect]] | None`.

- [ ] **Step 1: Write the failing tests**

The fixture is a two-column page: left column contains `scene recon-` / `struction quality`, right column contains the same phrase without hyphenation.

```python
def test_normalize_stitches_hyphenation():
    assert anchors.normalize("recon-\nstruction") == "reconstruction"


def test_find_rects_matches_hyphenated_quote(two_column_pdf):
    page = fitz.open(two_column_pdf)[0]
    rects = anchors.find_rects(page, "scene reconstruction quality")
    assert len(rects) >= 1


def test_find_rects_returns_empty_for_absent_quote(two_column_pdf):
    assert anchors.find_rects(fitz.open(two_column_pdf)[0], "quantum banana") == []


def test_locate_falls_back_one_page(two_column_pdf):
    doc = fitz.open(two_column_pdf)
    assert anchors.locate(doc, 1, "scene reconstruction quality") is not None
```

- [ ] **Step 2: Run and confirm failure**, then implement.

`find_rects` tries in order: `page.search_for(quote)`; the de-hyphenated form; a whitespace-normalized regex over `page.get_text("blocks")` with a rectangle computed from the matching span bboxes; otherwise `[]`. `locate` searches the requested page, then ±`tolerance_pages`.

- [ ] **Step 3: Run the tests** → PASS. **Step 4: Commit** — `git commit -m "feat: anchor verbatim quotes to page rectangles"`.

---

### Task 6: Verify the map before anything is written

**Files:**
- Create: `paper_atlas/verify.py`, `scripts/verify_quotes.py`, `tests/test_verify.py`

**Interfaces:**
- Consumes: `paper_atlas.anchors.locate`.
- Produces: `@dataclass class Report: errors: list[str]; warnings: list[str]; highlight_count: int`; `verify(map_dict: dict, doc, density: str = "normal") -> Report`.

- [ ] **Step 1: Write the failing tests**

```python
def test_missing_quote_is_an_error(valid_map, doc):
    valid_map["chain"][0]["quote"] = "this sentence does not exist in the paper"
    report = verify.verify(valid_map, doc)
    assert any("quote not found" in e for e in report.errors)


def test_inferred_field_requires_basis_quote(valid_map, doc):
    valid_map["choices"][0]["cost_inferred"] = True
    report = verify.verify(valid_map, doc)
    assert any("basis_quote" in e for e in report.errors)


def test_density_cap_is_enforced(valid_map, doc):
    valid_map["chain"] = valid_map["chain"] * 30
    assert any("exceeds" in e for e in verify.verify(valid_map, doc).errors)


def test_valid_map_has_no_errors(valid_map, doc):
    assert verify.verify(valid_map, doc).errors == []
```

- [ ] **Step 2: Run, confirm failure, implement.**

Rules: every `quote` must `locate` (else `"quote not found: <field>"`); every `*_inferred: true` needs a `basis_quote` that locates; `highlight_count` counts claim + chain + choices + figures + limits; cap 20 / 30. `scripts/verify_quotes.py` exits non-zero on errors.

- [ ] **Step 3: Run the tests** → PASS. **Step 4: Commit** — `git commit -m "feat: verify map quotes, inference basis and density cap"`.

---

### Task 7: Write annotations into the PDF

**Files:**
- Create: `paper_atlas/annotate.py`, `scripts/annotate.py`, `tests/test_annotate.py`

**Interfaces:**
- Consumes: `anchors.locate`, `verify.verify`.
- Produces:
  - `@dataclass class Planned: id: str; role: str; color: str; comment: str; page: int; quote: str`
  - `plan(map_dict: dict, doc, lang: str = "zh") -> list[Planned]`
  - `apply(pdf_path: Path, planned: list[Planned], doc, force: bool = False) -> dict` → `{"added": int, "skipped": int, "missing": list[str]}`

- [ ] **Step 1: Write the failing tests**

```python
def test_comment_never_equals_quote(valid_map, doc):
    p = annotate.plan(valid_map, doc)[0]
    assert anchors.normalize(p.comment) != anchors.normalize(p.quote)


def test_apply_then_reapply_adds_nothing(fixture_pdf, valid_map):
    doc = fitz.open(fixture_pdf)
    planned = annotate.plan(valid_map, doc)
    first = annotate.apply(fixture_pdf, planned, doc)
    assert first["added"] == len(planned)
    second = annotate.apply(fixture_pdf, planned, fitz.open(fixture_pdf))
    assert second["added"] == 0 and second["skipped"] == len(planned)


def test_backup_is_written_once(fixture_pdf, valid_map):
    doc = fitz.open(fixture_pdf)
    annotate.apply(fixture_pdf, annotate.plan(valid_map, doc), doc)
    backup = fixture_pdf.with_suffix(".paper-atlas.bak.pdf")
    assert backup.exists()
    mtime = backup.stat().st_mtime_ns
    annotate.apply(fixture_pdf, annotate.plan(valid_map, fitz.open(fixture_pdf)), fitz.open(fixture_pdf))
    assert backup.stat().st_mtime_ns == mtime


def test_roles_get_distinct_colors(valid_map, doc):
    colors = {p.role: p.color for p in annotate.plan(valid_map, doc)}
    assert len(set(colors.values())) == len(colors)
```

- [ ] **Step 2: Run, confirm failure, implement.**

Roles and colors: `claim` `#ffd400`, `chain` `#f19837`, `choice` `#5fb236`, `figure` `#2ea8e5`, `limit` `#ff6666`. Each annotation sets `/Contents`, `/C`, `/Zotero:Color`, `/Zotero:AuthorName` = `Paper Atlas`, `/Zotero:Key` = `pa-<paperkey>-<entryid>`, `/NM` = same key. Idempotency reads existing `/Zotero:Key` values from the open document and skips matches; `force=True` deletes Paper Atlas annotations first. Backup is created only when absent.

- [ ] **Step 3: Run the tests** → PASS. **Step 4: Commit** — `git commit -m "feat: write idempotent, role-colored Zotero-readable annotations"`.

---

### Task 8: End-to-end on NICE-SLAM

**Files:**
- Create: `reference/example-nice-slam.md`, `reference/example-nice-slam.json`, `docs/superpowers/specs/m0-result.md` (append)

**Interfaces:**
- Consumes: all CLIs from Tasks 3–7.
- Produces: the acceptance artifact.

- [ ] **Step 1: Stage the PDF** into `work/nice-slam.pdf` (download from arXiv `2112.12130` with `urllib`; if the network refuses, ask the user for a copy — do not invent content).
- [ ] **Step 2:** `python scripts/extract.py work/nice-slam.pdf --out work/nice-slam/` and inspect `structure.json` plus the crops.
- [ ] **Step 3:** Write `reference/example-nice-slam.json` following `map-schema.md`: ≥5 choices with `alternative`/`cost` (inferred ones with `basis_quote`), ≥8 figures/tables with `caveat`, ≤20 highlights.
- [ ] **Step 4:** `python scripts/verify_quotes.py reference/example-nice-slam.json --pdf work/nice-slam.pdf` → exit 0.
- [ ] **Step 5:** `python scripts/annotate.py reference/example-nice-slam.json --pdf work/nice-slam.pdf --dry-run`, then `--apply`, then `--apply` again and confirm `added: 0`.
- [ ] **Step 6:** Ask the user to open the annotated copy in Zotero and confirm the five role colors, comments and the one-click **文件 → 导入批注** promotion. Record the outcome.
- [ ] **Step 7: Commit** — `git commit -m "test: NICE-SLAM end-to-end acceptance artifact"`.

---

### Task 9: The skill itself

**Files:**
- Create: `SKILL.md`, `reference/map-schema.md`, `reference/map-example.md`, `tests/test_docs.py`

**Interfaces:**
- Consumes: the CLI flags shipped in Tasks 3–7.
- Produces: the file an agent loads.

- [ ] **Step 1: Write the failing doc test**

```python
def test_skill_frontmatter_and_scripts_exist():
    text = Path("SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\nname: paper-atlas\n")
    for script in ["find_paper.py", "extract.py", "verify_quotes.py", "annotate.py", "doctor.py"]:
        assert f"scripts/{script}" in text
        assert Path("scripts", script).exists()


def test_skill_states_the_hard_rules():
    text = Path("SKILL.md").read_text(encoding="utf-8")
    for phrase in ["never translate", "20", "Import Annotations", "basis_quote"]:
        assert phrase.lower() in text.lower()
```

- [ ] **Step 2: Run it** → FAIL (files missing).
- [ ] **Step 3: Write `SKILL.md`**

Frontmatter `name: paper-atlas` and a `description:` that triggers on "summarize this paper / 理清这篇论文的脉络 / annotate this PDF in Zotero", naming CS papers, Zotero, and the map. Body sections, in order: When to use; Hard rules (no translated PDF, verbatim quotes, inference marking, 20-highlight cap, no guessing coordinates, never write `zotero.sqlite`); Workflow (locate → extract → look at crops → draft map → verify → annotate → tell the user to click Import Annotations); Map schema pointer; Quality bar (what makes a choice column good, what "it did not prove" means); Failure handling table from spec §7.7; Bilingual rules.

- [ ] **Step 4: Write `reference/map-schema.md` and `reference/map-example.md`** (the schema table from spec §7.3 plus the NICE-SLAM example rendered as Markdown).
- [ ] **Step 5: Run the tests** → PASS. **Step 6: Commit** — `git commit -m "feat: add SKILL.md body, map schema and worked example"`.

---

### Task 10: Distribution and bilingual docs

**Files:**
- Create: `README.md`, `README.zh-CN.md`, `docs/install.md`, `tests/test_readme.py`

**Interfaces:**
- Consumes: everything above.
- Produces: the GitHub front door.

- [ ] **Step 1: Failing test**

```python
def test_readme_first_screen_explains_the_click():
    for name in ["README.md", "README.zh-CN.md"]:
        text = Path(name).read_text(encoding="utf-8")
        assert "Import Annotations" in text or "导入批注" in text
        assert "pip install -r requirements.txt" in text
```

- [ ] **Step 2:** Write both READMEs with the same five blocks: what it does (one paragraph + one screenshot placeholder), install (`git clone` into the skills directory, `python scripts/bootstrap.py`), first run, the two-stage annotation story, troubleshooting table (Zotero version, file locked, no text layer).
- [ ] **Step 3:** `docs/install.md` covers Claude Code, DeepSeek Harness and generic `~/.agents/skills/` paths.
- [ ] **Step 4: Run tests** → PASS. **Step 5: Commit** — `git commit -m "docs: bilingual README, install guide and troubleshooting"`.

---

### Task 11: Pressure test the skill

**Files:**
- Create: `docs/pressure-test.md`

- [ ] **Step 1: Baseline.** Dispatch a fresh subagent with only: "Summarize `work/nice-slam.pdf`" and no skill. Record where it drifts: no decisions, no evidence mapping, quotes not from the paper.
- [ ] **Step 2: With the skill.** Dispatch a fresh subagent with `SKILL.md` and the same paper. Check: map has ≥5 decisions with alternatives, every quote resolves, ≤20 highlights, no invented numbers.
- [ ] **Step 3: Fix the skill** to close the failures the baseline exposed; re-run Step 2.
- [ ] **Step 4: Write `docs/pressure-test.md`** with baseline failures, skill run, and what changed.
- [ ] **Step 5: Commit** — `git commit -m "test: pressure-test the skill against a baseline agent"`.

---

## Self-Review Notes

- Spec §7.6 (bilingual) is covered by Task 9 Step 3 (language rules) and Task 10; §9's translation constraints appear in the Global Constraints and Task 9's hard rules.
- Spec §10 acceptance maps to Task 8 Steps 4–6 and Task 11.
- Spec §11 M0 maps to Task 2; the fallback ladder lives in the spec §10 and is referenced in Task 2's opening line.
- Deferred on purpose: `zotero_api.py` and child-note creation (v2 per spec §5.3).
