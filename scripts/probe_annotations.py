"""M0 probe: write Zotero-readable highlights, then check what Zotero imported.

This script exists to answer one question before anything else is built:
does Zotero show, and import, annotations that another program wrote into
the PDF? Run it on a throwaway copy, open that copy in Zotero, then run
with --check-db.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paper_atlas.doctor import _zotero_data_dir  # noqa: E402

AUTHOR = "Paper Atlas"
YELLOW = (1.0, 0.831, 0.0)
QUOTES = ["quick brown fox", "lazy dog"]
COMMENTS = ["Probe: claim marker", "Probe: choice marker"]


def _pdf_string(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return f"({escaped})"


def _select_targets(page) -> list[tuple[str, str]]:
    """Prefer the canned English sentence; otherwise quote the document itself."""
    canned = [
        (quote, comment)
        for quote, comment in zip(QUOTES, COMMENTS)
        if page.search_for(quote)
    ]
    if len(canned) == 2:
        return canned

    found: list[tuple[str, str]] = []
    for block in page.get_text("blocks"):
        line = " ".join(block[4].split())
        if 15 <= len(line) <= 120 and page.search_for(line):
            found.append((line, COMMENTS[len(found)]))
        if len(found) == 2:
            break
    return found


def write_probe(pdf_path: Path, out_path: Path, prefix: str = "pa-probe") -> list[str]:
    """Add two highlights carrying Zotero's private keys; return their keys."""
    doc = pymupdf.open(str(pdf_path))
    page = doc[0]
    targets = _select_targets(page)
    if len(targets) < 2:
        raise SystemExit("could not find two quotable lines in the first page")

    keys: list[str] = []
    for index, (quote, comment) in enumerate(targets, start=1):
        rects = page.search_for(quote)
        annot = page.add_highlight_annot(rects[0])
        annot.set_colors(stroke=YELLOW)
        annot.set_info(content=comment, title=AUTHOR)
        annot.update()
        key = f"{prefix}-{index}"
        doc.xref_set_key(annot.xref, "Zotero:AuthorName", _pdf_string(AUTHOR))
        doc.xref_set_key(annot.xref, "Zotero:Key", _pdf_string(key))
        keys.append(key)
    doc.save(str(out_path))
    doc.close()
    return keys


def check_db() -> int:
    data_dir = _zotero_data_dir()
    if data_dir is None:
        print("no Zotero data directory found")
        return 1
    conn = sqlite3.connect(f"file:{data_dir / 'zotero.sqlite'}?mode=ro", uri=True)
    total = conn.execute("select count(*) from itemAnnotations").fetchone()[0]
    external = conn.execute(
        "select count(*) from itemAnnotations where isExternal=1"
    ).fetchone()[0]
    print(f"annotations: {total}, external: {external}")
    for row in conn.execute(
        "select type, comment, color, isExternal from itemAnnotations "
        "order by rowid desc limit 10"
    ):
        print("  ", row)
    conn.close()
    return 0 if external else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", nargs="?", help="PDF to probe")
    parser.add_argument("--out", help="output copy (default: <name>.probe.pdf)")
    parser.add_argument("--key-prefix", default="pa-probe")
    parser.add_argument(
        "--check-db", action="store_true", help="count external annotations in Zotero"
    )
    args = parser.parse_args(argv)

    if args.check_db:
        return check_db()

    if not args.pdf:
        parser.error("pdf is required unless --check-db is used")

    source = Path(args.pdf)
    out = Path(args.out) if args.out else source.with_suffix(".probe.pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    keys = write_probe(source, out, args.key_prefix)
    print(f"wrote {len(keys)} highlights: {', '.join(keys)}")
    print(f"copy: {out}")
    print()
    print("Next: drag the copy into Zotero, open it in the reader, and look for")
    print("two yellow highlights whose comments read 'Probe: claim marker' and")
    print("'Probe: choice marker'. Then run: python scripts/probe_annotations.py --check-db")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
