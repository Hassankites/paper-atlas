"""Build a throwaway Zotero-shaped library for tests."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pymupdf

SCHEMA = """
create table items (itemID integer primary key, itemTypeID int, libraryID int, key text);
create table itemData (itemID int, fieldID int, valueID int);
create table itemDataValues (valueID integer primary key, value text);
create table fields (fieldID int, fieldName text);
create table itemAttachments (itemID int, parentItemID int, path text, contentType text);
create table deletedItems (itemID integer primary key);
"""

TITLE = "NICE-SLAM: Neural Implicit Scalable Encoding for SLAM"


@dataclass
class Fixture:
    data_dir: Path
    pdf: Path

    def remove_pdf(self) -> None:
        self.pdf.unlink()


def build(root: Path) -> Fixture:
    # A non-ASCII parent directory on purpose: the real data dir is under one.
    data_dir = root / "测试用户" / "Zotero"
    storage = data_dir / "storage" / "ATTACH01"
    storage.mkdir(parents=True)
    pdf = storage / "paper.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "NICE-SLAM", fontsize=12)
    doc.save(pdf)
    doc.close()

    con = sqlite3.connect(data_dir / "zotero.sqlite")
    con.executescript(SCHEMA)
    con.execute("insert into items values (1, 1, 1, 'PARENT01')")
    con.execute("insert into items values (2, 1, 1, 'ATTACH01')")
    con.execute("insert into fields values (1, 'title')")
    con.execute("insert into itemDataValues values (1, ?)", (TITLE,))
    con.execute("insert into itemData values (1, 1, 1)")
    con.execute(
        "insert into itemAttachments values (2, 1, 'storage:paper.pdf', 'application/pdf')"
    )
    # A deleted paper and a standalone attachment, both matching the query:
    # neither should come back from a search.
    con.execute("insert into items values (3, 1, 1, 'DELETED1')")
    con.execute("insert into itemDataValues values (2, ?)", ("NICE-SLAM (old copy)",))
    con.execute("insert into itemData values (3, 1, 2)")
    con.execute("insert into deletedItems values (3)")
    con.execute("insert into items values (4, 1, 1, 'ATTACH02')")
    con.execute("insert into itemDataValues values (3, ?)", ("NICE-SLAM.pdf",))
    con.execute("insert into itemData values (4, 1, 3)")
    con.execute(
        "insert into itemAttachments values (4, null, 'storage:scan.pdf', 'application/pdf')"
    )
    con.commit()
    con.close()
    return Fixture(data_dir=data_dir, pdf=pdf)
