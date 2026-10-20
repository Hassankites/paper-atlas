"""CLI: python scripts/render_map.py map.json [--pdf P] [--out DIR] [--lang zh]"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pymupdf  # noqa: E402

from paper_atlas import render, verify  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render the Markdown map")
    parser.add_argument("map", help="path to map.json")
    parser.add_argument("--pdf", help="locate the quotes and print their real pages")
    parser.add_argument("--out", help="output directory")
    parser.add_argument("--lang", choices=sorted(render.HEADINGS), default="zh")
    args = parser.parse_args(argv)

    map_dict = json.loads(Path(args.map).read_text(encoding="utf-8"))
    if args.pdf:
        for correction in verify.fill_pages(map_dict, pymupdf.open(args.pdf)):
            print(f"page fix : {correction}")
    out_dir = render.resolve_out_dir(map_dict, Path(args.out) if args.out else None)
    target = render.write(map_dict, out_dir, lang=args.lang)
    print(f"map  : {target}")
    print(f"json : {target.with_name('map.json')}")
    if args.lang == "en" and render.has_cjk(target.read_text(encoding="utf-8")):
        print(
            "note : the headings are English but the body is still Chinese; --lang "
            "does not translate prose — write the map body in English instead"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
