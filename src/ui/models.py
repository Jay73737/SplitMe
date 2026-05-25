from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class VideoMeta:
    video_id: str
    title: str
    thumb_url: str
    duration_iso: str

    @property
    def youtube_url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"

    
    @classmethod
    def from_search(cls, raw_items: list[dict]) -> list["VideoMeta"]:
        vids: list[VideoMeta] = []
        for it in raw_items:
            vid = it["id"].get("videoId")
            if not vid:
                continue
            sn = it["snippet"]
            vids.append(cls(
                video_id     = vid,
                title        = sn["title"],
                thumb_url    = sn["thumbnails"]["medium"]["url"],
                duration_iso = "",          
            ))
        return vids