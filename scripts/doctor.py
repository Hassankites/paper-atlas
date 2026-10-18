"""CLI wrapper: python scripts/doctor.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paper_atlas import doctor  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(doctor.main(sys.argv[1:]))
