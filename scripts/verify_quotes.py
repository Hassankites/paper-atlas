"""CLI: python scripts/verify_quotes.py map.json --pdf paper.pdf"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pymupdf  # noqa: E402

from paper_atlas import verify  # noqa: E402

pymupdf.TOOLS.mupdf_display_errors(False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a map against its PDF")
    parser.add_argument("map", help="path to map.json")
    parser.add_argument("--pdf", required=True, help="the paper's PDF")
    parser.add_argument("--density", choices=sorted(verify.CAPS), default="normal")
    parser.add_argument("--lang", choices=["zh", "en"], default="zh")
    args = parser.parse_args(argv)

    map_dict = json.loads(Path(args.map).read_text(encoding="utf-8"))
    doc = pymupdf.open(args.pdf)
    for correction in verify.fill_pages(map_dict, doc):
        print(f"page fix   : {correction}")
    report = verify.verify(map_dict, doc, density=args.density, lang=args.lang)

    print(f"highlights : {report.highlight_count} (cap {verify.CAPS[args.density]})")
    for warning in report.warnings:
        print(f"warning    : {warning}")
    for error in report.errors:
        print(f"error      : {error}")
    print("ok" if report.ok else "failed")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
