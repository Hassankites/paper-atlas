import pytest

from paper_atlas import zotero
from tests.fixtures.build_zotero_fixture import build


@pytest.fixture()
def library(tmp_path):
    return build(tmp_path)


def test_snapshot_is_removed_on_close(library):
    conn = zotero.connect_ro(library.data_dir)
    snapshot = conn.snapshot_dir
    assert snapshot.exists()
    conn.close()
    assert not snapshot.exists()


def test_snapshot_is_removed_when_used_as_a_context_manager(library):
    with zotero.connect_ro(library.data_dir) as conn:
        snapshot = conn.snapshot_dir
        assert snapshot.exists()
    assert not snapshot.exists()
