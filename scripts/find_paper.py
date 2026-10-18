"""CLI: python scripts/find_paper.py "nice-slam" [--data-dir PATH]"""

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paper_atlas import zotero  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Find a paper and its PDF in Zotero")
    parser.add_argument("query", help="part of the title")
    parser.add_argument("--data-dir", help="Zotero data directory")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args(argv)

    try:
        data_dir = Path(args.data_dir) if args.data_dir else zotero.default_data_dir()
    except FileNotFoundError as error:
        print(f"error: {error}")
        print("hint: pass --data-dir, or set ZOTERO_DATA to the folder with zotero.sqlite")
        return 2

    conn = None
    try:
        conn = zotero.connect_ro(data_dir)
        hits = zotero.find_item(conn, args.query, args.limit)
    except (OSError, sqlite3.DatabaseError) as error:
        print(f"error: cannot read {data_dir}: {error}")
        return 2
    finally:
        if conn is not None:
            conn.close()

    if not hits:
        print(f"no item matches {args.query!r} in {data_dir}")
        return 1

    for hit in hits:
        print(f"{hit.item_id}\t{hit.key}\t{hit.title}")
        print(f"\tPDF: {hit.pdf_path if hit.pdf_path else 'not attached'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
