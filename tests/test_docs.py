from pathlib import Path


def test_skill_frontmatter_and_scripts_exist():
    text = Path("SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\nname: paper-atlas\n")
    for script in [
        "doctor.py",
        "find_paper.py",
        "extract.py",
        "verify_quotes.py",
        "annotate.py",
        "render_map.py",
    ]:
        assert f"scripts/{script}" in text
        assert Path("scripts", script).exists()


def test_skill_states_the_hard_rules():
    text = Path("SKILL.md").read_text(encoding="utf-8").lower()
    for phrase in [
        "never translate",
        "basis_quote",
        "import annotations",
        "ask",
        "20",
        "paper-atlas/",
    ]:
        assert phrase in text, phrase


def test_skill_carries_the_voice_guide():
    text = Path("SKILL.md").read_text(encoding="utf-8")
    assert "## Voice" in text
    assert "No metaphors" in text
    assert "15 words" in text
    assert "lieflat-less-ai-tone" in text


def test_skill_names_the_two_field_traps():
    text = Path("SKILL.md").read_text(encoding="utf-8")
    assert "several items match" in text.lower()
    assert "no crop" in text.lower()
    assert "subagent" in text.lower()


def test_schema_doc_exists():
    schema = Path("reference/map-schema.md").read_text(encoding="utf-8")
    for field in ["claim", "chain", "choices", "figures", "limits", "basis_quote", "note"]:
        assert field in schema
