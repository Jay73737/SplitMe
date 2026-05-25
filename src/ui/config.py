from __future__ import annotations
import json, pathlib

BASE_DIR   = pathlib.Path(__file__).resolve().parent
CONFIG_F   = (BASE_DIR / "config.json") if (BASE_DIR / "config.json").exists() \
             else (BASE_DIR.parent / "config.json")


def _load_key() -> str:
    if CONFIG_F.exists():
        try:
            cfg = json.loads(CONFIG_F.read_text("utf-8"))
            return (
                cfg.get("api_key")
                or cfg.get("YOUTUBE_API_KEY")
                or cfg.get("youtube_api_key")
                or ""
            )
        except json.JSONDecodeError:
            pass
    return ""


YOUTUBE_API_KEY = _load_key()