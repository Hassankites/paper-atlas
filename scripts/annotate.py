"""CLI: python scripts/annotate.py map.json --pdf paper.pdf [--apply]"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pymupdf  # noqa: E402

from paper_atlas import anchors, annotate, verify  # noqa: E402

pymupdf.TOOLS.mupdf_display_errors(False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write a map into the PDF")
    parser.add_argument("map", help="path to map.json")
    parser.add_argument("--pdf", required=True, help="the paper's PDF")
    parser.add_argument("--apply", action="store_true", help="actually write")
    parser.add_argument("--force", action="store_true", help="replace earlier runs")
    parser.add_argument("--lang", choices=sorted(annotate.LABELS), default="zh")
    parser.add_argument("--density", choices=sorted(verify.CAPS), default="normal")
    args = parser.parse_args(argv)

    map_dict = json.loads(Path(args.map).read_text(encoding="utf-8"))
    doc = pymupdf.open(args.pdf)

    for correction in verify.fill_pages(map_dict, doc):
        print(f"page fix   : {correction}")

    report = verify.verify(map_dict, doc, density=args.density, lang=args.lang)
    if not report.ok:
        for error in report.errors:
            print(f"error      : {error}")
        print("refusing to write: fix the map first")
        return 1

    planned = annotate.plan(map_dict, doc, lang=args.lang)
    pdf_path = Path(args.pdf)
    backup = pdf_path.with_name(pdf_path.stem + annotate.BACKUP_SUFFIX)

    if not args.apply:
        print(f"file    : {pdf_path}")
        print(f"backup  : {backup}")
        print(
            "colors  : "
            + ", ".join(f"{role} {color}" for role, color in annotate.COLORS.items())
        )
        for item in planned:
            found = anchors.locate(doc, item.page, item.quote)
            if found:
                page_index, rects = found
                width = round(sum(rect.width for rect in rects))
                where = f"p.{page_index + 1} ({width}pt wide, {len(rects)} line(s))"
            else:
                where = "NOT FOUND"
            print(f"{item.role:7s} {where:34s} {item.id}")
        print(f"dry run: {len(planned)} annotations, nothing written")
        return 0

    result = annotate.apply(pdf_path, planned, doc, force=args.force)
    print(f"file    : {pdf_path}")
    print(f"backup  : {backup}")
    print(f"added   : {result['added']}")
    print(f"skipped : {result['skipped']}")
    if result["missing"]:
        for missing in result["missing"]:
            print(f"missing : {missing}")
        print("some quotes could not be located; they were not written")
        return 1

    print()
    print("Next: open the PDF in Zotero, then File -> Import Annotations")
    print("to turn these read-only highlights into editable Zotero annotations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
