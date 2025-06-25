from __future__ import annotations
import pathlib, subprocess, tempfile, requests
from .config  import YOUTUBE_API_KEY
from .models  import VideoMeta

_API = "https://www.googleapis.com/youtube/v3"



def search(query: str, *, limit: int = 8) -> list[VideoMeta]:
    if not YOUTUBE_API_KEY:
        raise RuntimeError("Missing YOUTUBE_API_KEY in config.json")
    r = requests.get(
        f"{_API}/search",
        params=dict(part="snippet", q=query, maxResults=limit,
                    type="video", key=YOUTUBE_API_KEY),
        timeout=8,
    )
    r.raise_for_status()
    videos = VideoMeta.from_search(r.json()["items"])

  
    if videos:
        _fill_durations(videos)
    return videos


def download_audio(video_id: str) -> pathlib.Path:
    """Return cached / freshly-downloaded .mp3 path for given video ID."""
    out = pathlib.Path(tempfile.gettempdir()) / f"{video_id}.mp3"
    if out.exists():
        return out
    subprocess.run(
        ["yt-dlp", "-f", "bestaudio",
         "--extract-audio", "--audio-format", "mp3",
         "-o", str(out), f"https://youtu.be/{video_id}"],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    return out



def _fill_durations(videos: list[VideoMeta]) -> None:
    ids = ",".join(v.video_id for v in videos)
    r   = requests.get(
        f"{_API}/videos",
        params=dict(part="contentDetails", id=ids, key=YOUTUBE_API_KEY),
        timeout=6,
    )
    if r.status_code != 200:
        return
    iso_map = {it["id"]: _iso_to_clock(it["contentDetails"]["duration"])
               for it in r.json()["items"]}
    for v in videos:
        object.__setattr__(v, "duration_iso", iso_map.get(v.video_id, ""))


def _iso_to_clock(iso: str) -> str:
    import re
    h = m = s = 0
    for val, unit in re.findall(r"(\d+)([HMS])", iso):
        if unit == "H":
            h = int(val)
        elif unit == "M":
            m = int(val)
        elif unit == "S":
            s = int(val)
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"