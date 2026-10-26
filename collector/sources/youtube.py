"""YouTube 채널 RSS (키 불필요). 채널 ID는 채널 페이지 소스의 "channelId" 값."""
from __future__ import annotations

from collector.sources._common import date_from_struct, get

import feedparser

FEED = "https://www.youtube.com/feeds/videos.xml"


def fetch(channel_id: str, keywords: list[str] | None = None):
    feed = feedparser.parse(get(FEED, params={"channel_id": channel_id}).content)
    channel = (feed.feed or {}).get("title")
    for e in feed.entries:
        desc = e.get("media_description") or e.get("summary") or ""
        text = f"{e.get('title', '')} {desc}".lower()
        if keywords and not any(k.lower() in text for k in keywords):
            continue
        thumbs = e.get("media_thumbnail") or []
        yield {
            "kind": "video",
            "title": e.get("title") or "",
            "url": e.get("link"),
            "doi": None,
            "authors": None,
            "venue": channel or e.get("author"),
            "published_at": date_from_struct(e.get("published_parsed")),
            "text": desc,
            "raw": {"video_id": e.get("yt_videoid"), "thumbnail": thumbs[0].get("url") if thumbs else None},
        }
