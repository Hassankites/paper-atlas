"""Environment self-check for paper-atlas."""

from __future__ import annotations

import os
import platform
import sys
from importlib.metadata import version
from pathlib import Path


def _zotero_data_dir() -> Path | None:
    """Return the first candidate directory that holds a Zotero database."""
    candidates: list[Path] = []
    env = os.environ.get("ZOTERO_DATA")
    if env:
        candidates.append(Path(env))
    candidates.append(Path.home() / "Zotero")
    candidates.append(Path.home() / "Library" / "Application Support" / "Zotero")
    for candidate in candidates:
        try:
            if (candidate / "zotero.sqlite").exists():
                return candidate
        except OSError:
            continue
    return None


def check() -> dict:
    problems: list[str] = []
    python_version = platform.python_version()
    if sys.version_info < (3, 10):
        problems.append(f"python {python_version} is older than 3.10")

    try:
        import pymupdf  # noqa: F401

        pymupdf = version("pymupdf")
    except Exception:
        pymupdf = None
        problems.append("missing: pymupdf (pip install -r requirements.txt)")

    data_dir = _zotero_data_dir()
    if data_dir is None:
        problems.append("missing: Zotero data directory (set ZOTERO_DATA)")

    return {
        "python": python_version,
        "pymupdf": pymupdf,
        "zotero_data": str(data_dir) if data_dir else None,
        "problems": problems,
    }


def main(argv: list[str] | None = None) -> int:
    report = check()
    print(f"python      : {report['python']}")
    print(f"pymupdf     : {report['pymupdf'] or 'missing'}")
    print(f"zotero data : {report['zotero_data'] or 'missing'}")
    if report["problems"]:
        for problem in report["problems"]:
            print(f"problem     : {problem}")
        return 1
    print("ok")
    return 0
