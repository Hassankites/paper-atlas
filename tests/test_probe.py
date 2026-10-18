import pymupdf
import pytest

from scripts.probe_annotations import write_probe

SENTENCE = "The quick brown fox jumps over the lazy dog."


@pytest.fixture()
def probe_pdf(tmp_path):
    pdf = tmp_path / "in.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 100), SENTENCE, fontsize=12)
    doc.save(pdf)
    return pdf


def test_probe_writes_two_highlights(probe_pdf, tmp_path):
    keys = write_probe(probe_pdf, tmp_path / "out.pdf")
    assert len(keys) == 2

    out = pymupdf.open(tmp_path / "out.pdf")
    annots = [a for a in out[0].annots() if a.type[1] == "Highlight"]
    assert len(annots) == 2


def test_probe_falls_back_to_text_from_the_document(tmp_path):
    pdf = tmp_path / "in.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text(
        (72, 100),
        "This paper studies neural implicit scene representations for SLAM.",
        fontsize=12,
    )
    page.insert_text(
        (72, 130),
        "We build a hierarchical feature grid so large scenes stay detailed.",
        fontsize=12,
    )
    doc.save(pdf)

    keys = write_probe(pdf, tmp_path / "out.pdf")
    assert len(keys) == 2


def test_probe_sets_a_yellow_stroke(probe_pdf, tmp_path):
    write_probe(probe_pdf, tmp_path / "out.pdf")
    out = pymupdf.open(tmp_path / "out.pdf")
    annot = [a for a in out[0].annots() if a.type[1] == "Highlight"][0]
    stroke = annot.colors.get("stroke")
    assert stroke is not None
    assert abs(stroke[0] - 1.0) < 0.01
    assert abs(stroke[1] - 0.83) < 0.02
    assert abs(stroke[2] - 0.0) < 0.01
    assert out.xref_get_key(annot.xref, "C")[0] == "array"


def test_probe_sets_zotero_keys_and_a_distinct_comment(probe_pdf, tmp_path):
    keys = write_probe(probe_pdf, tmp_path / "out.pdf")
    out = pymupdf.open(tmp_path / "out.pdf")
    page = out[0]
    annots = [a for a in page.annots() if a.type[1] == "Highlight"]

    for annot, key in zip(annots, keys):
        covered = page.get_textbox(annot.rect).strip()
        assert annot.info["content"].strip()
        assert annot.info["content"].strip() != covered
        assert out.xref_get_key(annot.xref, "Zotero:AuthorName") == ("string", "Paper Atlas")
        assert out.xref_get_key(annot.xref, "Zotero:Color") == ("string", "#ffd400")
        assert out.xref_get_key(annot.xref, "Zotero:Key") == ("string", key)
