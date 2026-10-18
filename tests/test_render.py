import pytest

from paper_atlas import render


@pytest.fixture()
def map_dict():
    return {
        "paper": {"title": "NICE-SLAM", "zotero_key": "NICESLAM"},
        "claim": {"text": "分层网格换掉单个 MLP", "quote": "we present NICE-SLAM", "page": 0},
        "chain": [
            {"id": "c1", "step": "前人做法", "text": "iMAP 只能全局更新", "quote": "updated globally", "page": 1}
        ],
        "choices": [
            {
                "id": "d1",
                "choice": "三层网格",
                "quote": "three grids",
                "page": 2,
                "alternative": "单分辨率网格",
                "alternative_inferred": True,
                "basis_quote": "one feature grid",
                "solves": "局部更新",
                "cost": "参数更多",
            }
        ],
        "figures": [
            {
                "label": "Table 5",
                "page": 7,
                "caption_quote": "Table 5. Ablation Study",
                "question": "每项贡献多少",
                "supports": "冻结解码器",
                "key_numbers": "5 次平均",
                "caveat": "只有 6 个场景",
            }
        ],
        "strength": [{"text": "跑了 5 次", "quote": "5 times"}],
        "concepts": [{"term": "occupancy", "gloss": "占据概率", "page": 2}],
        "limits": [{"text": "颜色会遗忘", "quote": "forgetting"}],
        "terms": [{"en": "frame-to-model", "zh": "帧到模型"}],
    }


def test_render_has_every_section(map_dict):
    text = render.render(map_dict, lang="zh")
    for heading in [
        "## 一句话主张",
        "## 因果链",
        "## 选择点",
        "## 图表证据",
        "## 证据强度",
        "## 前置概念",
        "## 术语表",
    ]:
        assert heading in text


def test_render_marks_inferred_columns(map_dict):
    text = render.render(map_dict, lang="zh")
    assert "（推断）" in text


def test_render_turns_zero_based_pages_into_printed_pages(map_dict):
    text = render.render(map_dict, lang="zh")
    assert "p.1" in text and "p.3" in text


def test_render_english_headings(map_dict):
    text = render.render(map_dict, lang="en")
    assert "## The Claim" in text and "## Decision Points" in text
    assert "| Term | Chinese |" in text


def test_default_out_dir_sits_under_paper_atlas(map_dict, tmp_path):
    path = render.default_out_dir(map_dict, base=tmp_path)
    assert path.parent == tmp_path
    assert "NICESLAM" in path.name


def test_resolve_out_dir_falls_back_when_home_is_unwritable(map_dict, tmp_path, monkeypatch):
    blocker = tmp_path / "blocked"
    blocker.write_text("not a directory")
    monkeypatch.setattr(render, "default_out_dir", lambda m, base=None: blocker / "sub")
    monkeypatch.chdir(tmp_path)
    out = render.resolve_out_dir(map_dict)
    assert out == tmp_path / "paper-atlas" / "sub"


def test_render_separates_pain_and_novelty(map_dict):
    map_dict["pain"] = [
        {
            "who": "多房间扫描",
            "symptom": "重建变糊、追踪漂移",
            "cost": "得重扫一遍",
            "quote": "significant performance drops",
            "page": 0,
        }
    ]
    map_dict["novelty"] = [
        {
            "what": "分层网格支持局部更新",
            "versus": "iMAP 的单个 MLP",
            "borrowed": False,
            "why": "第一次让隐式 SLAM 具备局部可更新性",
            "quote": "hierarchical scene representation",
            "page": 0,
        },
        {
            "what": "ConvONet 预训练解码器",
            "versus": "ConvONet",
            "borrowed": True,
            "why": "直接借用，未改",
            "quote": "pre-trained as part of ConvONet",
            "page": 2,
        },
    ]
    text = render.render(map_dict, lang="zh")
    assert "## 痛点" in text
    assert "## 创新点" in text
    assert "借来的" in text
    assert "多房间扫描" in text and "分层网格支持局部更新" in text
    assert "代价是 得重扫" not in text and "代价是得重扫" in text


def test_render_english_pain_and_novelty_headings(map_dict):
    map_dict["pain"] = [{"who": "multi-room", "symptom": "blurry", "cost": "rescan", "page": 0}]
    map_dict["novelty"] = [
        {"what": "hierarchical grid", "versus": "single MLP", "borrowed": False, "page": 0},
        {"what": "ConvONet decoder", "versus": "ConvONet", "borrowed": True, "page": 2},
    ]
    text = render.render(map_dict, lang="en")
    assert "## Why it hurts" in text and "## What is new" in text
    assert "Borrowed" in text


def test_write_creates_the_markdown_file(map_dict, tmp_path):
    path = render.write(map_dict, tmp_path / "out", lang="zh")
    assert path.name == "map.md"
    assert "## 选择点" in path.read_text(encoding="utf-8")
