import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if sys.platform == "win32":
    # Python 3.12 applies a restrictive ACL when a directory is created with
    # mode 0o700. Under the sandboxed process token the directory then cannot
    # be listed even by its creator, which breaks tempfile.mkdtemp, pytest's
    # tmp_path and pip's unpack step. Ignore the mode on Windows.
    _real_mkdir = os.mkdir

    def _mkdir_without_mode(path, mode=0o777, *args, **kwargs):
        return _real_mkdir(path, 0o777, *args, **kwargs)

    os.mkdir = _mkdir_without_mode

# pytest.ini points --basetemp at work/pt; pytest creates the leaf but not its
# parent, and a fresh clone has no work/ directory yet.
(ROOT / "work").mkdir(exist_ok=True)
