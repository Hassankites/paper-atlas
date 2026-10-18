from paper_atlas import doctor


def test_check_reports_environment_keys():
    report = doctor.check()
    assert set(report) == {"python", "pymupdf", "zotero_data", "problems"}
    assert report["python"].startswith("3.")
    assert isinstance(report["problems"], list)


def test_main_fails_when_a_problem_exists(monkeypatch):
    monkeypatch.setattr(doctor, "check", lambda: {
        "python": "3.12.10",
        "pymupdf": None,
        "zotero_data": None,
        "problems": ["missing: pymupdf"],
    })
    assert doctor.main([]) == 1


def test_main_succeeds_when_clean(monkeypatch):
    monkeypatch.setattr(doctor, "check", lambda: {
        "python": "3.12.10",
        "pymupdf": "1.26.0",
        "zotero_data": r"C:\Users\x\Zotero",
        "problems": [],
    })
    assert doctor.main([]) == 0
