from pathlib import Path

import pymupdf
import pytest

from paper_atlas import extract
from tests.fixtures.build_paper_fixture import build, build_chinese


@pytest.fixture()
def paper_pdf(tmp_path):
    return build(tmp_path / "paper.pdf")


def test_structure_has_pages_with_sized_blocks(paper_pdf):
    structure = extract.extract_structure(paper_pdf)
    assert len(structure["pages"]) == 2
    block = structure["pages"][0]["blocks"][0]
    assert set(block) >= {"bbox", "text", "size"}
    assert block["size"] > 0


def test_detects_sections_and_figures(paper_pdf):
    structure = extract.extract_structure(paper_pdf)
    assert any(
        section["title"].startswith("1 Introduction")
        for section in structure["sections"]
    )
    labels = [figure["label"] for figure in structure["figures"]]
    assert "Figure 1" in labels and "Table 2" in labels


def test_crop_file_is_created_and_non_empty(paper_pdf, tmp_path):
    structure = extract.extract_structure(paper_pdf)
    crops = extract.render_figures(structure, paper_pdf, tmp_path / "figs")
    figure = next(item for item in crops if item["label"] == "Figure 1")
    assert figure["crop"]
    assert Path(figure["crop"]).stat().st_size > 1000


def test_figure_without_image_degrades_to_caption_only(paper_pdf, tmp_path):
    structure = extract.extract_structure(paper_pdf)
    crops = extract.render_figures(structure, paper_pdf, tmp_path / "figs")
    table = next(item for item in crops if item["label"] == "Table 2")
    assert table["crop"] is None


def test_extract_cli_refuses_a_textless_pdf(tmp_path):
    from scripts.extract import main

    pdf = tmp_path / "scan.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.draw_rect(pymupdf.Rect(72, 72, 400, 400), color=(0, 0, 0))
    doc.save(pdf)
    doc.close()

    assert main([str(pdf), "--out", str(tmp_path / "out")]) == 2


def test_textless_pdf_is_detected(tmp_path):
    pdf = tmp_path / "scan.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.draw_rect(pymupdf.Rect(72, 72, 400, 400), color=(0, 0, 0))
    doc.save(pdf)
    doc.close()

    structure = extract.extract_structure(pdf)
    assert extract.is_textless(structure) is True


def test_a_normal_pdf_is_not_textless(paper_pdf):
    assert extract.is_textless(extract.extract_structure(paper_pdf)) is False


def test_detects_chinese_caption_labels(tmp_path):
    pdf = build_chinese(tmp_path / "cn.pdf")
    structure = extract.extract_structure(pdf)
    labels = [figure["label"] for figure in structure["figures"]]
    assert "Figure 1" in labels
    assert "Table 2" in labels
