"""CLI: python scripts/extract.py paper.pdf --out work/paper"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paper_atlas import extract  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract structure and figure crops")
    parser.add_argument("pdf")
    parser.add_argument("--out", help="output directory (default: work/<stem>)")
    parser.add_argument("--dpi", type=int, default=160)
    args = parser.parse_args(argv)

    pdf = Path(args.pdf)
    out_dir = Path(args.out) if args.out else Path("work") / pdf.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    structure = extract.extract_structure(pdf)
    crops = extract.render_figures(structure, pdf, out_dir / "figs", dpi=args.dpi)
    structure["figures"] = crops

    target = out_dir / "structure.json"
    target.write_text(json.dumps(structure, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"pages     : {len(structure['pages'])}")
    print(f"sections  : {len(structure['sections'])}")
    print(f"figures   : {len(crops)}  ({sum(1 for c in crops if c['crop'])} with a crop)")
    print(f"structure : {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
