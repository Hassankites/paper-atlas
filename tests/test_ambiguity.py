import pymupdf
import pytest

from paper_atlas import anchors, verify


@pytest.fixture()
def duplicate_pdf(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 100), "alpha beta gamma delta", fontsize=10)
    page.insert_text((72, 400), "alpha beta gamma delta", fontsize=10)
    doc.save(tmp_path / "dup.pdf")
    doc.close()
    return tmp_path / "dup.pdf"


def test_count_occurrences_counts_repeats(duplicate_pdf):
    page = pymupdf.open(duplicate_pdf)[0]
    assert anchors.count_occurrences(page, "alpha beta gamma delta") == 2


def test_count_occurrences_is_zero_for_absent_text(duplicate_pdf):
    page = pymupdf.open(duplicate_pdf)[0]
    assert anchors.count_occurrences(page, "quantum banana") == 0


def test_find_rects_returns_one_occurrence_only(duplicate_pdf):
    page = pymupdf.open(duplicate_pdf)[0]
    rects = anchors.find_rects(page, "alpha beta gamma delta")
    union = rects[0]
    for rect in rects[1:]:
        union = union | rect
    assert union.height < 40


def test_gutter_of_fifteen_points_keeps_columns_apart():
    left = pymupdf.Rect(72, 100, 150, 112)
    right = pymupdf.Rect(165, 100, 240, 112)
    assert len(anchors._group_by_line([left, right])) == 2


def test_verify_rejects_an_ambiguous_quote(duplicate_pdf):
    doc = pymupdf.open(duplicate_pdf)
    map_dict = {
        "claim": {
            "text": "x",
            "quote": "alpha beta gamma delta",
            "page": 0,
        }
    }
    report = verify.verify(map_dict, doc)
    assert any("occurs 2 times" in error for error in report.errors)
