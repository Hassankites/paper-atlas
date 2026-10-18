"""Two-column page with a hyphenated word break, for anchor tests."""

from pathlib import Path

import pymupdf


def build(path: Path) -> Path:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)

    # Left column: the phrase is split across a line break with a hyphen.
    page.insert_text((50, 100), "The model improves scene recon-", fontsize=10)
    page.insert_text((50, 114), "struction quality on Replica.", fontsize=10)

    # Right column: no copy of the phrase, so only stitching can find it.
    page.insert_text((300, 100), "We measure geometry quality against", fontsize=10)
    page.insert_text((300, 114), "two baselines.", fontsize=10)

    doc.new_page(width=595, height=842)
    doc.save(path)
    doc.close()
    return path
