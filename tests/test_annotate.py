import re

import pymupdf
import pytest

from paper_atlas import anchors, annotate
from tests.fixtures.build_paper_fixture import build

BODY = "This paper studies neural implicit SLAM for large indoor scenes."
HEADING = "1 Introduction"
FIGURE_CAPTION = "Figure 1: Reconstruction quality on Replica."


@pytest.fixture()
def fixture_pdf(tmp_path):
    return build(tmp_path / "paper.pdf")


@pytest.fixture()
def doc(fixture_pdf):
    return pymupdf.open(fixture_pdf)


@pytest.fixture()
def valid_map():
    return {
        "paper": {"title": "NICE-SLAM", "zotero_key": "ABCD1234"},
        "claim": {"text": "hierarchical encoding for scalable SLAM", "quote": BODY, "page": 0},
        "chain": [
            {"id": "c1", "step": "problem", "text": "single MLP cannot scale", "quote": BODY, "page": 0}
        ],
        "choices": [
            {
                "id": "d1",
                "choice": "hierarchical feature grid",
                "quote": HEADING,
                "page": 0,
                "alternative": "one global MLP",
                "alternative_inferred": True,
                "basis_quote": BODY,
                "solves": "local updates",
                "cost": "more parameters",
            }
        ],
        "figures": [
            {
                "label": "Figure 1",
                "page": 1,
                "caption_quote": FIGURE_CAPTION,
                "supports": "hierarchical grid gives local updates",
                "caveat": "Replica only",
            }
        ],
        "strength": [],
        "concepts": [],
        "limits": [],
    }


def test_comment_never_equals_quote(valid_map, doc):
    planned = annotate.plan(valid_map, doc)
    assert len(planned) == 4
    for item in planned:
        assert anchors.normalize(item.comment) != anchors.normalize(item.quote)
        assert len(item.comment) <= 200


def test_note_overrides_the_template(valid_map, doc):
    valid_map["choices"][0]["note"] = "拿全局 MLP 换局部更新，参数多了但稳。"
    choice = next(
        item for item in annotate.plan(valid_map, doc) if item.role == "choice"
    )
    assert "拿全局 MLP 换局部更新" in choice.comment
    assert choice.comment.startswith("[选择]")


def test_note_is_clipped_to_200_characters(valid_map, doc):
    valid_map["claim"]["note"] = "很长" * 300
    claim = next(item for item in annotate.plan(valid_map, doc) if item.role == "claim")
    assert claim.comment.count("很长") > 50
    assert len(claim.comment) <= 200


def test_comments_do_not_leak_internal_ids(valid_map, doc):
    for item in annotate.plan(valid_map, doc):
        assert not re.search(r"\b[cdl]\d\b", item.comment), item.comment


def test_chain_comment_names_the_step_instead_of_an_id(valid_map, doc):
    chain_comment = next(
        item.comment for item in annotate.plan(valid_map, doc) if item.role == "chain"
    )
    assert "problem" in chain_comment


def test_multiline_quote_gets_one_quad_per_line(tmp_path):
    pdf = tmp_path / "multi.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Dense visual SLAM is a fundamental problem", fontsize=10)
    page.insert_text((72, 114), "in computer vision with many applications", fontsize=10)
    page.insert_text((72, 128), "in autonomous driving and robotics.", fontsize=10)
    doc.save(pdf)
    doc.close()

    map_dict = {
        "paper": {"zotero_key": "MULTI"},
        "claim": {
            "text": "SLAM matters",
            "quote": "Dense visual SLAM is a fundamental problem in computer vision "
            "with many applications in autonomous driving and robotics",
            "page": 0,
        },
    }
    annotate.apply(
        pdf,
        annotate.plan(map_dict, pymupdf.open(pdf)),
        pymupdf.open(pdf),
    )

    out = pymupdf.open(pdf)
    page = out[0]
    annot = [a for a in page.annots() if a.type[1] == "Highlight"][0]
    # Three lines => three quads => twelve corner points, not one big box.
    assert len(annot.vertices) == 12


def test_plan_uses_stable_ids(valid_map, doc):
    first = [item.id for item in annotate.plan(valid_map, doc)]
    second = [item.id for item in annotate.plan(valid_map, doc)]
    assert first == second
    assert all(item.startswith("pa-ABCD1234-") for item in first)


def test_roles_get_distinct_colors(valid_map, doc):
    colors = {item.role: item.color for item in annotate.plan(valid_map, doc)}
    assert set(colors) == {"claim", "chain", "choice", "figure"}
    assert len(set(colors.values())) == len(colors)


def test_apply_then_reapply_adds_nothing(fixture_pdf, valid_map):
    planned = annotate.plan(valid_map, pymupdf.open(fixture_pdf))
    first = annotate.apply(fixture_pdf, planned, pymupdf.open(fixture_pdf))
    assert first["added"] == len(planned)

    second = annotate.apply(fixture_pdf, planned, pymupdf.open(fixture_pdf))
    assert second["added"] == 0
    assert second["skipped"] == len(planned)


def test_backup_is_written_once(fixture_pdf, valid_map):
    planned = annotate.plan(valid_map, pymupdf.open(fixture_pdf))
    annotate.apply(fixture_pdf, planned, pymupdf.open(fixture_pdf))
    backup = fixture_pdf.with_suffix(".paper-atlas.bak.pdf")
    assert backup.exists()
    stamp = backup.stat().st_mtime_ns

    annotate.apply(fixture_pdf, planned, pymupdf.open(fixture_pdf))
    assert backup.stat().st_mtime_ns == stamp


def test_missing_quote_is_reported_and_not_written(fixture_pdf, valid_map):
    valid_map["chain"][0]["quote"] = "a sentence that is not in this pdf"
    planned = annotate.plan(valid_map, pymupdf.open(fixture_pdf))
    result = annotate.apply(fixture_pdf, planned, pymupdf.open(fixture_pdf))
    assert result["missing"] == ["pa-ABCD1234-c1"]
    assert result["added"] == len(planned) - 1


def test_written_annotations_are_highlights_with_zotero_keys(fixture_pdf, valid_map):
    planned = annotate.plan(valid_map, pymupdf.open(fixture_pdf))
    annotate.apply(fixture_pdf, planned, pymupdf.open(fixture_pdf))

    out = pymupdf.open(fixture_pdf)
    annots = [a for page in out for a in (page.annots() or []) if a.type[1] == "Highlight"]
    assert len(annots) == len(planned)
    for annot in annots:
        assert out.xref_get_key(annot.xref, "Zotero:AuthorName") == ("string", "Paper Atlas")
        assert out.xref_get_key(annot.xref, "Zotero:Key")[0] == "string"
        assert out.xref_get_key(annot.xref, "C")[0] == "array"
