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
    assert len(rects) == 1
    assert rects[0].x0 < 280  # the left column, where the word was split


def test_find_rects_returns_empty_for_absent_quote(two_column_pdf):
    page = pymupdf.open(two_column_pdf)[0]
    assert anchors.find_rects(page, "quantum banana") == []


def test_locate_falls_back_one_page(two_column_pdf):
    doc = pymupdf.open(two_column_pdf)
    result = anchors.locate(doc, 1, "scene reconstruction quality")
    assert result is not None
    page_index, rects = result
    assert page_index == 0 and rects
