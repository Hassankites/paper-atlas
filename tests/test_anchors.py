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


def test_hyphen_inside_a_word_survives_a_line_break(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 100), "we compare fine-", fontsize=10)
    page.insert_text((72, 114), "tuning against adapters", fontsize=10)
    doc.save(tmp_path / "hyphen.pdf")

    page = pymupdf.open(tmp_path / "hyphen.pdf")[0]
    assert anchors.find_rects(page, "fine-tuning against adapters") != []


def test_hyphen_mismatch_between_quote_and_page_still_matches(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 100), "we freeze the pretrained weights", fontsize=10)
    doc.save(tmp_path / "pretrained.pdf")

    page = pymupdf.open(tmp_path / "pretrained.pdf")[0]
    assert anchors.find_rects(page, "freeze the pre-trained weights") != []


def test_normalize_unpacks_ligatures():
    assert anchors.normalize("ﬁne-tuning") == "fine-tuning"
    assert anchors.normalize("eﬀicient") == "efficient"


def test_find_rects_ignores_terminal_punctuation(two_column_pdf):
    page = pymupdf.open(two_column_pdf)[0]
    # Hyphenated, and the page word ends with a full stop the quote omits.
    assert anchors.find_rects(page, "scene reconstruction quality on Replica") != []


def test_far_pair_is_rejected_when_no_contiguous_copy_exists(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 100), "alpha", fontsize=10)
    page.insert_text((72, 400), "beta", fontsize=10)
    doc.save(tmp_path / "far.pdf")

    page = pymupdf.open(tmp_path / "far.pdf")[0]
    assert anchors.find_rects(page, "alpha beta") == []


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


def _page_with(tmp_path, lines):
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    for text, x, y, size in lines:
        page.insert_text((x, y), text, fontsize=size)
    path = tmp_path / "page.pdf"
    doc.save(path)
    return pymupdf.open(path)[0]


def test_a_lost_minus_sign_is_not_a_match(tmp_path):
    page = _page_with(tmp_path, [("the score changes by -1 points", 72, 100, 11)])
    assert anchors.find_rects(page, "the score changes by 1 points") == []
    assert anchors.count_occurrences(page, "the score changes by 1 points") == 0


def test_a_quote_with_its_minus_sign_still_matches(tmp_path):
    page = _page_with(tmp_path, [("the score changes by -1 points", 72, 100, 11)])
    assert anchors.find_rects(page, "the score changes by -1 points") != []


def test_a_numeric_range_survives_dash_styles(tmp_path):
    page = _page_with(tmp_path, [("we sweep 10-20 steps", 72, 100, 11)])
    assert anchors.find_rects(page, "we sweep 10–20 steps") != []
    assert anchors.find_rects(page, "we sweep 1020 steps") == []


def test_a_repeated_sentence_does_not_merge_two_lines(tmp_path):
    page = _page_with(
        tmp_path,
        [
            ("WE PROPOSE a routing policy", 72, 100, 11),
            ("WE PROPOSE a routing policy", 72, 114, 11),
        ],
    )
    rects = anchors.find_rects(page, "WE PROPOSE a routing policy")
    assert len(rects) == 1
    assert rects[0].height < 20  # one line, not the union of both


def test_occurrences_are_case_insensitive(tmp_path):
    # A repeated sentence that differs only in case is still two matches, and
    # an ambiguous quote must be reported, not silently anchored to one copy.
    page = _page_with(
        tmp_path,
        [
            ("We propose a robust method", 72, 100, 11),
            ("WE PROPOSE A ROBUST METHOD", 72, 114, 11),
        ],
    )
    assert anchors.count_occurrences(page, "We propose a robust method") == 2


def test_occurrences_respect_word_boundaries(tmp_path):
    page = _page_with(tmp_path, [("the method beats every methodology", 72, 100, 11)])
    assert anchors.count_occurrences(page, "method") == 1


def test_a_tall_glyph_cannot_stretch_the_quad_into_the_next_line():
    # Adam p8: the formula makes one box 22 pt tall inside a 10 pt line; a naive
    # union paints the paragraph below it.
    line = [
        pymupdf.Rect(72, 100, 120, 110),
        pymupdf.Rect(124, 96, 150, 118),
        pymupdf.Rect(154, 100, 200, 110),
    ]
    rects = anchors._group_by_line(line)
    assert len(rects) == 1
    assert (rects[0].y0, rects[0].y1) == (100, 110)


def test_a_hyphenated_pair_does_not_cover_the_column_beside_it(tmp_path):
    page = _page_with(
        tmp_path,
        [
            ("unrelated left text", 72, 100, 11),
            ("fine-", 380, 100, 11),
            ("tuning quality is better", 380, 114, 11),
        ],
    )
    rects = anchors.find_rects(page, "fine-tuning quality")
    assert len(rects) == 2
    assert rects[0].x0 > 370
    assert "unrelated" not in " ".join(page.get_textbox(rect) for rect in rects)
