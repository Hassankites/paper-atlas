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


def test_an_invented_number_is_an_error(valid_map, doc):
    valid_map["claim"]["text"] = "speedup is 999999 percent"
    report = verify.verify(valid_map, doc)
    assert any("999999" in error for error in report.errors)


def test_a_number_from_the_paper_is_accepted(valid_map, doc):
    valid_map["claim"]["text"] = "see Figure 1 for the gain"
    report = verify.verify(valid_map, doc)
    assert not any("does not appear" in error for error in report.errors)


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
    valid_map["chain"] = [
        dict(item, id=f"c{index}") for index, item in enumerate(valid_map["chain"] * 20, 1)
    ]
    assert verify.verify(valid_map, doc, density="normal").errors
    assert verify.verify(valid_map, doc, density="detailed").errors == []


def test_an_inferred_strength_may_not_carry_a_quote(valid_map, doc):
    # The quote would be highlighted-free but still read as the paper's words.
    valid_map["strength"] = [
        {
            "text": "作者只跑了六个场景",
            "inferred": True,
            "quote": "This sentence does not exist in the paper at all.",
            "basis_quote": BODY,
            "page": 0,
        }
    ]
    report = verify.verify(valid_map, doc)
    assert any("must not carry a quote" in error for error in report.errors)


def test_an_inferred_strength_needs_a_real_basis(valid_map, doc):
    valid_map["strength"] = [
        {"text": "作者只跑了六个场景", "inferred": True, "basis_quote": BODY, "page": 0}
    ]
    assert verify.verify(valid_map, doc).errors == []


def test_a_pain_quote_is_checked_too(valid_map, doc):
    valid_map["pain"] = [
        {
            "who": "扫描员",
            "symptom": "一间房重来",
            "cost": "重扫",
            "quote": "a sentence that is nowhere in this pdf",
            "page": 0,
        }
    ]
    assert any("pain[1]" in error for error in verify.verify(valid_map, doc).errors)


def test_a_novelty_row_without_a_quote_is_an_error(valid_map, doc):
    valid_map["novelty"] = [{"what": "分层网格", "versus": "MLP", "origin": "new", "page": 0}]
    assert any("missing quote" in error for error in verify.verify(valid_map, doc).errors)


def test_a_figure_evidence_quote_is_checked(valid_map, doc):
    valid_map["figures"][0]["evidence_quote"] = "1.2 dB better, which is not in the pdf"
    assert any(
        "evidence_quote" in error for error in verify.verify(valid_map, doc).errors
    )


def test_two_entries_may_not_share_an_id(valid_map, doc):
    valid_map["chain"][0]["id"] = "claim"
    assert any("duplicate annotation id" in error for error in verify.verify(valid_map, doc).errors)


def test_an_overlong_comment_is_an_error_not_a_silent_cut(valid_map, doc):
    valid_map["claim"]["note"] = "很长" * 200
    assert any("chars" in error for error in verify.verify(valid_map, doc).errors)


def test_an_unknown_novelty_origin_is_an_error(valid_map, doc):
    valid_map["novelty"] = [
        {"what": "分层网格", "versus": "MLP", "origin": "borrowed-ish", "quote": BODY, "page": 0}
    ]
    assert any("origin must be" in error for error in verify.verify(valid_map, doc).errors)


def test_the_old_borrowed_flag_only_warns(valid_map, doc):
    valid_map["novelty"] = [
        {"what": "分层网格", "versus": "MLP", "borrowed": True, "quote": BODY, "page": 0}
    ]
    report = verify.verify(valid_map, doc)
    assert report.errors == []
    assert any("origin" in warning for warning in report.warnings)


def test_existing_annotations_count_towards_the_cap(tmp_path, valid_map):
    # A second map on the same PDF would push it past the reader's budget.
    from paper_atlas import annotate

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 100), BODY, fontsize=10)
    page.insert_text((72, 200), HEADING, fontsize=10)
    page.insert_text((72, 300), FIGURE_CAPTION, fontsize=10)
    for index in range(18):
        annot = page.add_highlight_annot(pymupdf.Rect(72, 96 + index * 0.1, 300, 104))
        annot.update()
        doc.xref_set_key(annot.xref, "Zotero:Key", f"(pa-OLD-anchor{index})")
    doc.save(tmp_path / "used.pdf")
    used = pymupdf.open(tmp_path / "used.pdf")

    report = verify.verify(valid_map, used)
    assert any("already carries" in error for error in report.errors)
    assert annotate.our_keys(used)  # the helper the check relies on
