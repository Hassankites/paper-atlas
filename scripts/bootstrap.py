"""One-time setup: make sure pymupdf and pytest are importable.

Tries a virtual environment first; falls back to the user site when venv
creation fails (non-ASCII paths on Windows can break ensurepip).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "requirements.txt"


def _run(cmd: list) -> int:
    return subprocess.call([str(part) for part in cmd])


def _importable(interpreter: Path) -> bool:
    return interpreter.exists() and _run([interpreter, "-c", "import pymupdf, pytest"]) == 0


def main() -> int:
    venv = ROOT / ".venv"
    venv_python = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not venv_python.exists():
        _run([sys.executable, "-m", "venv", str(venv)])

    for interpreter in (venv_python, Path(sys.executable)):
        if not interpreter.exists():
            continue
        if _run([interpreter, "-m", "pip", "install", "-q", "-r", str(REQUIREMENTS)]) == 0:
            if _importable(interpreter):
                print(f"ready: {interpreter}")
                return 0

    for interpreter in (Path(sys.executable), venv_python):
        if not interpreter.exists():
            continue
        _run([interpreter, "-m", "pip", "install", "--user", "-q", "-r", str(REQUIREMENTS)])
        if _importable(interpreter):
            print(f"ready (user site): {interpreter}")
            return 0

    print("failed: install pymupdf and pytest manually", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
