"""Entry point for the packaged SplitMe backend."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _bootstrap_paths() -> Path:
    """Ensure project root is importable and return it."""
    if getattr(sys, "frozen", False):  # running from PyInstaller bundle
        root = Path(getattr(sys, "_MEIPASS", Path.cwd()))
    else:
        root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def main() -> None:
    root = _bootstrap_paths()

    # Allow the Electron host to override host/port; defaults match the dev env
    host = os.environ.get("SPLITME_BACKEND_HOST", "127.0.0.1")
    port = int(os.environ.get("SPLITME_BACKEND_PORT", "5050"))
    log_level = os.environ.get("SPLITME_BACKEND_LOG_LEVEL", "info")

    # Some third-party libs (torch/demucs) assume CWD == project root
    os.chdir(root)

    import uvicorn  # pylint: disable=import-outside-toplevel

    uvicorn.run("api.server:app", host=host, port=port, log_level=log_level)


if __name__ == "__main__":
    main()
