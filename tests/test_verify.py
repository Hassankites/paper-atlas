import pymupdf
import pytest

from paper_atlas import verify
from tests.fixtures.build_paper_fixture import build

TITLE = "Neural Implicit Scalable Encoding"
BODY = "This paper studies neural implicit SLAM for large indoor scenes."
HEADING = "1 Introduction"
FIGURE_CAPTION = "Figure 1: Reconstruction quality on Replica."


@pytest.fixture()
def doc(tmp_path):
    return pymupdf.open(build(tmp_path / "paper.pdf"))


@pytest.fixture()
def valid_map():
    return {
        "paper": {"title": TITLE},
        "claim": {"text": "hierarchical encoding", "quote": BODY, "page": 0},
        "chain": [
            {
                "id": "c1",
                "step": "problem",
                "text": "scaling is hard",
                "quote": BODY,
                "page": 0,
            }
        ],
        "choices": [
            {
                "id": "d1",
                "choice": "hierarchical grid",
                "quote": HEADING,
                "page": 0,
                "alternative": "one global MLP",
                "cost": "more parameters",
            }
        ],
        "figures": [
            {
                "label": "Figure 1",
                "page": 1,
                "caption_quote": FIGURE_CAPTION,
                "caveat": "only Replica",
            }
        ],
        "strength": [],
        "concepts": [],
        "limits": [],
    }


def test_valid_map_has_no_errors(valid_map, doc):
    report = verify.verify(valid_map, doc)
    assert report.errors == []
    assert report.highlight_count == 4


def test_missing_quote_is_an_error(valid_map, doc):
    valid_map["chain"][0]["quote"] = "this sentence does not exist in the paper"
    report = verify.verify(valid_map, doc)
    assert any("quote not found" in error for error in report.errors)


def test_inferred_field_requires_basis_quote(valid_map, doc):
    valid_map["choices"][0]["cost_inferred"] = True
    report = verify.verify(valid_map, doc)
    assert any("basis_quote" in error for error in report.errors)


def test_inferred_field_with_a_bad_basis_quote_is_an_error(valid_map, doc):
    valid_map["choices"][0]["alternative_inferred"] = True
    valid_map["choices"][0]["basis_quote"] = "no such sentence anywhere"
    report = verify.verify(valid_map, doc)
    assert any("basis_quote" in error and "not found" in error for error in report.errors)


def test_basis_quote_may_live_far_from_the_choice(tmp_path):
    doc = pymupdf.open()
    for _ in range(4):
        doc.new_page()
    doc[0].insert_text((72, 72), "the method uses a grid", fontsize=10)
    doc[3].insert_text((72, 72), "local BA keeps the tracking stable", fontsize=10)
    map_dict = {
        "choices": [
            {
                "id": "d1",
                "choice": "grid",
                "quote": "the method uses a grid",
                "page": 0,
                "alternative": "one MLP",
                "alternative_inferred": True,
                "basis_quote": "local BA keeps the tracking stable",
                "solves": "s",
                "cost": "c",
            }
        ]
    }
    assert verify.verify(map_dict, doc).errors == []


def test_comment_repeating_the_quote_is_an_error(valid_map, doc):
    # The fallback comment would be "[主张] " + the quote itself; Zotero erases
    # comments within ~10% edit distance of the highlighted text.
    valid_map["claim"]["text"] = BODY
    report = verify.verify(valid_map, doc)
    assert any("repeats the highlighted text" in error for error in report.errors)


def test_choice_without_an_alternative_is_an_error(valid_map, doc):
    valid_map["choices"][0]["alternative"] = ""
    report = verify.verify(valid_map, doc)
    assert any("alternative" in error for error in report.errors)


def test_density_cap_is_enforced(valid_map, doc):
    valid_map["chain"] = valid_map["chain"] * 30
    report = verify.verify(valid_map, doc)
    assert any("exceeds" in error for error in report.errors)


def test_detailed_density_raises_the_cap(valid_map, doc):
    valid_map["chain"] = valid_map["chain"] * 20
    assert verify.verify(valid_map, doc, density="normal").errors
    assert verify.verify(valid_map, doc, density="detailed").errors == []
