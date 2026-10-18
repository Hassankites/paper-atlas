from pathlib import Path


def test_readme_first_screen_explains_the_click():
    for name in ["README.md", "README.zh-CN.md"]:
        text = Path(name).read_text(encoding="utf-8")
        assert "Import Annotations" in text or "导入批注" in text


def test_readmes_state_install_and_map_location():
    for name in ["README.md", "README.zh-CN.md"]:
        text = Path(name).read_text(encoding="utf-8")
        assert "pip install -r requirements.txt" in text
        assert "paper-atlas/" in text


def test_readme_has_troubleshooting():
    text = Path("README.md").read_text(encoding="utf-8")
    assert "Troubleshooting" in text
    zh = Path("README.zh-CN.md").read_text(encoding="utf-8")
    assert "排错" in zh
