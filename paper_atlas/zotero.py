"""Read a Zotero library without touching the live database.

Zotero keeps `zotero.sqlite` in WAL mode and holds it open. A read-only
connection to the live file fails with "database is locked", so every read
goes through a snapshot copy of the database and its WAL files.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote


@dataclass(frozen=True)
class PaperHit:
    item_id: int
    key: str
    title: str
    pdf_path: Path | None


class LibraryConnection(sqlite3.Connection):
    """A connection that remembers the library and cleans up its snapshot."""

    data_dir: Path
    snapshot_dir: Path

    def close(self) -> None:
        try:
            super().close()
        finally:
            shutil.rmtree(self.snapshot_dir, ignore_errors=True)

    def __enter__(self) -> "LibraryConnection":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()


def default_data_dir() -> Path:
    candidates: list[Path] = []
    env = os.environ.get("ZOTERO_DATA")
    if env:
        candidates.append(Path(env))
    candidates.append(Path.home() / "Zotero")
    candidates.append(Path.home() / "Library" / "Application Support" / "Zotero")
    for candidate in candidates:
        if (candidate / "zotero.sqlite").exists():
            return candidate
    raise FileNotFoundError(
        "no Zotero data directory found; set ZOTERO_DATA to the folder "
        "that contains zotero.sqlite"
    )


def connect_ro(data_dir: Path) -> LibraryConnection:
    """Open a read-only snapshot of the library."""
    snapshot = Path(tempfile.gettempdir()) / f"paper-atlas-{uuid.uuid4().hex[:8]}"
    # Plain mkdir on purpose: tempfile.mkdtemp applies a 0o700 ACL on Windows
    # that sandboxed process tokens cannot write back into.
    snapshot.mkdir()
    for name in ("zotero.sqlite", "zotero.sqlite-wal", "zotero.sqlite-shm"):
        source = Path(data_dir) / name
        if source.exists():
            shutil.copy2(source, snapshot / name)
    database = snapshot / "zotero.sqlite"
    uri = f"file:{quote(database.as_posix())}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, factory=LibraryConnection)
    conn.row_factory = sqlite3.Row
    conn.data_dir = Path(data_dir)
    conn.snapshot_dir = snapshot
    return conn


def _like(term: str) -> str:
    """Escape the wildcards a paper title may contain (%, _, \\)."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def find_item(
    conn: sqlite3.Connection, query: str, limit: int = 5
) -> list[PaperHit]:
    # Attachments carry the filename as their title, and a deleted item still
    # sits in `items` until the trash is emptied; neither is a paper to map.
    has_trash = conn.execute(
        "select 1 from sqlite_master where type = 'table' and name = 'deletedItems'"
    ).fetchone()
    trash = (
        "and i.itemID not in (select itemID from deletedItems)"
        if has_trash
        else ""
    )
    rows = conn.execute(
        f"""
        select i.itemID as item_id, i.key as key, v.value as title
        from items i
        join itemData d on d.itemID = i.itemID
        join fields f on f.fieldID = d.fieldID and f.fieldName = 'title'
        join itemDataValues v on v.valueID = d.valueID
        where lower(v.value) like lower(?) escape '\\'
          and i.itemID not in (select itemID from itemAttachments)
          {trash}
        order by i.itemID desc
        limit ?
        """,
        (_like(query), limit),
    ).fetchall()

    data_dir = getattr(conn, "data_dir", None)
    return [
        PaperHit(
            item_id=row["item_id"],
            key=row["key"],
            title=row["title"],
            pdf_path=resolve_pdf(conn, row["item_id"], data_dir) if data_dir else None,
        )
        for row in rows
    ]


def resolve_pdf(
    conn: sqlite3.Connection, item_id: int, data_dir: Path | None
) -> Path | None:
    row = conn.execute(
        """
        select i.key as key, a.path as path
        from itemAttachments a
        join items i on i.itemID = a.itemID
        where a.parentItemID = ? and a.contentType = 'application/pdf'
        limit 1
        """,
        (item_id,),
    ).fetchone()
    if row is None or data_dir is None:
        return None

    stored = row["path"] or ""
    if stored.startswith("storage:"):
        candidate = Path(data_dir) / "storage" / row["key"] / stored[len("storage:") :]
    else:
        candidate = Path(stored)
    return candidate if candidate.exists() else None
