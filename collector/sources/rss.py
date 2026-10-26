"""일반 RSS/Atom 피드. sources.kind가 그대로 항목의 kind가 된다."""
from __future__ import annotations

import feedparser

from collector.sources._common import date_from_struct, get


def fetch(url: str, kind: str = "news"):
    feed = feedparser.parse(get(url).content)
    venue = (feed.feed or {}).get("title")
    for e in feed.entries:
        yield {
            "kind": kind,
            "title": " ".join((e.get("title") or "").split()),
            "url": e.get("link"),
            "doi": None,
            "authors": e.get("author"),
            "venue": venue,
            "published_at": date_from_struct(e.get("published_parsed") or e.get("updated_parsed")),
            "text": e.get("summary") or "",
            "raw": {},
        }
