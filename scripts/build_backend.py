#!/usr/bin/env python3
"""Build the SplitMe backend into a distributable binary using PyInstaller."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PYINSTALLER_MODULE = "PyInstaller"


def find_project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_tools() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ModuleNotFoundError as exc:  # pragma: no cover - user guidance path
        raise SystemExit(
            "PyInstaller is not installed. Install it with 'pip install pyinstaller'."
        ) from exc


def run_pyinstaller(target: Path, dist_dir: Path, work_dir: Path, clean: bool) -> None:
    cmd = [
        sys.executable,
        "-m",
        PYINSTALLER_MODULE,
        str(target),
        "--name",
        "SplitMeBackend",
        "--noconfirm",
        "--clean" if clean else "",
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(work_dir),
        "--specpath",
        str(target.parent),
        "--collect-all",
        "demucs",
        "--collect-all",
        "torchaudio",
        "--collect-all",
        "torch",
        "--collect-submodules",
        "api",
        "--collect-submodules",
        "yt_dlp",
        "--collect-submodules",
        "googleapiclient",
        "--collect-submodules",
        "librosa",
        "--collect-submodules",
        "soundfile",
        "--add-data",
        f"{target.parents[1] / 'config'}{';' if sys.platform == 'win32' else ':'}config",
        "--add-data",
        f"{target.parents[1] / 'assets'}{';' if sys.platform == 'win32' else ':'}assets",
        "--add-data",
        f"{target.parents[1] / 'data'}{';' if sys.platform == 'win32' else ':'}data",
    ]

    # Remove empty arguments that may have been inserted for optional flags
    cmd = [part for part in cmd if part]

    subprocess.check_call(cmd)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clear previous build artifacts before building.",
    )
    parser.add_argument(
        "--dist",
        default="dist/backend",
        help="Relative path for PyInstaller output directory.",
    )
    parser.add_argument(
        "--work",
        default="build/backend",
        help="Relative path for PyInstaller work directory.",
    )
    args = parser.parse_args()

    ensure_tools()

    root = find_project_root()
    target = root / "backend" / "main.py"
    dist_dir = root / args.dist
    work_dir = root / args.work

    dist_dir.parent.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    if args.clean and dist_dir.exists():
        shutil.rmtree(dist_dir)

    run_pyinstaller(target, dist_dir, work_dir, clean=args.clean)


if __name__ == "__main__":
    main()
