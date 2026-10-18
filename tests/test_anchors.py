import pymupdf
import pytest

from paper_atlas import anchors
from tests.fixtures.build_anchor_fixture import build


@pytest.fixture()
def two_column_pdf(tmp_path):
    return build(tmp_path / "two-column.pdf")


def test_normalize_stitches_hyphenation():
    assert anchors.normalize("recon-\nstruction") == "reconstruction"


def test_normalize_collapses_whitespace():
    assert anchors.normalize("scene   recon-\nstruction\tquality") == "scene reconstruction quality"


def test_find_rects_matches_hyphenated_quote(two_column_pdf):
    page = pymupdf.open(two_column_pdf)[0]
    rects = anchors.find_rects(page, "scene reconstruction quality")
    assert len(rects) >= 1
    assert all(rect.x0 < 280 for rect in rects)  # the left column, where it split


def test_find_rects_returns_empty_for_absent_quote(two_column_pdf):
    page = pymupdf.open(two_column_pdf)[0]
    assert anchors.find_rects(page, "quantum banana") == []


def test_find_rects_ignores_terminal_punctuation(two_column_pdf):
    page = pymupdf.open(two_column_pdf)[0]
    # Hyphenated, and the page word ends with a full stop the quote omits.
    assert anchors.find_rects(page, "scene reconstruction quality on Replica") != []


def test_find_rects_prefers_the_compact_occurrence(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 100), "alpha", fontsize=10)
    page.insert_text((72, 400), "beta", fontsize=10)  # a false, far-apart pairing
    page.insert_text((72, 600), "alpha beta", fontsize=10)  # the real one
    doc.save(tmp_path / "gaps.pdf")

    page = pymupdf.open(tmp_path / "gaps.pdf")[0]
    rects = anchors.find_rects(page, "alpha beta")
    union = rects[0]
    for rect in rects[1:]:
        union = union | rect
    assert union.height < 40


def test_locate_falls_back_one_page(two_column_pdf):
    doc = pymupdf.open(two_column_pdf)
    result = anchors.locate(doc, 1, "scene reconstruction quality")
    assert result is not None
    page_index, rects = result
    assert page_index == 0 and rects
