"""Build a two-page paper-shaped PDF for extraction tests."""

from pathlib import Path

import pymupdf


def build(path: Path) -> Path:
    doc = pymupdf.open()
    first = doc.new_page(width=595, height=842)
    first.insert_text((72, 80), "Neural Implicit Scalable Encoding", fontsize=18)
    first.insert_text(
        (72, 140),
        "This paper studies neural implicit SLAM for large indoor scenes.",
        fontsize=10,
    )
    first.insert_text((72, 200), "1 Introduction", fontsize=12)
    first.insert_text(
        (72, 220),
        "Dense SLAM has made progress but scaling up remains hard.",
        fontsize=10,
    )

    second = doc.new_page(width=595, height=842)
    second.draw_rect(
        pymupdf.Rect(72, 120, 400, 280), color=(0, 0, 0), fill=(0.8, 0.8, 0.8)
    )
    second.insert_text(
        (72, 300), "Figure 1: Reconstruction quality on Replica.", fontsize=9
    )
    second.insert_text((72, 380), "Table 2: Tracking results on TUM.", fontsize=9)

    doc.save(path)
    doc.close()
    return path


def build_chinese(path: Path) -> Path:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 100), "图 1: 重建质量对比。", fontsize=9, fontname="china-s")
    page.insert_text((72, 200), "表 2 追踪结果。", fontsize=9, fontname="china-s")
    doc.save(path)
    doc.close()
    return path
