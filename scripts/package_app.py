#!/usr/bin/env python3
"""End-to-end packaging workflow for the SplitMe desktop application."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
BACKEND_DIST = PROJECT_ROOT / "dist" / "backend" / "SplitMeBackend"


def run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    human = " ".join(cmd)
    print(f"→ {human}")
    subprocess.check_call(cmd, cwd=cwd, env=env)


def ensure_frontend_deps() -> None:
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.exists():
        run(["npm", "install"], cwd=FRONTEND_DIR)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-backend",
        action="store_true",
        help="Do not rebuild the backend (use existing dist/backend artifacts).",
    )
    parser.add_argument(
        "--platform",
        choices=["mac", "win", "linux", "all"],
        default="all",
        help="Target platform for electron-builder (default: all).",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove previous release output before building.",
    )
    args = parser.parse_args()

    if args.clean:
        release_dir = PROJECT_ROOT / "release"
        if release_dir.exists():
            shutil.rmtree(release_dir)

    if not args.skip_backend or not BACKEND_DIST.exists():
        cmd = [sys.executable, "scripts/build_backend.py"]
        if args.clean:
            cmd.append("--clean")
        run(cmd, cwd=PROJECT_ROOT)

    if not BACKEND_DIST.exists():
        raise SystemExit(
            "Backend bundle missing. Run scripts/build_backend.py before packaging the Electron app."
        )

    ensure_frontend_deps()

    script_map = {
        "mac": "dist:mac",
        "win": "dist:win",
        "linux": "dist:linux",
        "all": "dist",
    }
    target_script = script_map[args.platform]

    run(["npm", "run", target_script], cwd=FRONTEND_DIR)


if __name__ == "__main__":
    main()
