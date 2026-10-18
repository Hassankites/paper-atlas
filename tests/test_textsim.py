from paper_atlas import textsim


LONG_QUOTE = (
    "significant performance drops are observed in both the dense reconstruction "
    "and camera tracking accuracy"
)


def test_label_plus_the_quote_is_too_similar():
    # Zotero clears a comment within ~10% edit distance of the highlighted text.
    assert textsim.too_similar("[存疑] " + LONG_QUOTE, LONG_QUOTE)


def test_a_short_label_does_not_save_a_copied_quote():
    assert textsim.too_similar("[主张] " + LONG_QUOTE, LONG_QUOTE)


def test_a_real_note_is_far_enough():
    note = "[选择] 粗层故意做糙，专门管没看见的地方；细活留给中/细层。"
    assert not textsim.too_similar(note, LONG_QUOTE)


def test_normalisation_ignores_case_and_whitespace():
    assert textsim.normalized("  A  B\nC ") == "a b c"
