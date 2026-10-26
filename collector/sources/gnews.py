"""Google News RSS 키워드 검색(비공식). 형식이 바뀔 수 있어 이 소스만 실패하도록 격리한다."""
from __future__ import annotations

from urllib.parse import urlencode

import feedparser

from collector.sources._common import date_from_struct, get

BASE = "https://news.google.com/rss/search"
LOCALE = {
    "ko": {"hl": "ko", "gl": "KR", "ceid": "KR:ko"},
    "en": {"hl": "en-US", "gl": "US", "ceid": "US:en"},
}


def fetch(query: str, lang: str = "ko", days: int = 14):
    q = query if "when:" in query else f"{query} when:{days}d"
    params = {"q": q, **LOCALE.get(lang, LOCALE["ko"])}
    feed = feedparser.parse(get(f"{BASE}?{urlencode(params)}").content)
    for e in feed.entries:
        source = (e.get("source") or {}).get("title")
        title = e.get("title") or ""
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3]
        yield {
            "kind": "news",
            "title": title.strip(),
            "url": e.get("link"),
            "doi": None,
            "authors": None,
            "venue": source,
            "published_at": date_from_struct(e.get("published_parsed")),
            "text": e.get("summary") or "",
            "raw": {},
        }
