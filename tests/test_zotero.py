import sqlite3

import pytest

from paper_atlas import zotero
from tests.fixtures.build_zotero_fixture import build


@pytest.fixture()
def library(tmp_path):
    return build(tmp_path)


def test_find_item_matches_title_case_insensitively(library):
    conn = zotero.connect_ro(library.data_dir)
    hits = zotero.find_item(conn, "nice-slam")
    assert len(hits) == 1
    assert hits[0].title.startswith("NICE-SLAM")


def test_resolve_pdf_returns_existing_path(library):
    conn = zotero.connect_ro(library.data_dir)
    hit = zotero.find_item(conn, "NICE-SLAM")[0]
    assert hit.pdf_path is not None and hit.pdf_path.exists()


def test_resolve_pdf_returns_none_when_file_missing(library):
    library.remove_pdf()
    conn = zotero.connect_ro(library.data_dir)
    assert zotero.resolve_pdf(conn, 1, library.data_dir) is None


def test_connect_ro_cannot_write(library):
    conn = zotero.connect_ro(library.data_dir)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("insert into items (itemID) values (99)")


def test_default_data_dir_honours_the_env_var(library, monkeypatch):
    monkeypatch.setenv("ZOTERO_DATA", str(library.data_dir))
    assert zotero.default_data_dir() == library.data_dir
