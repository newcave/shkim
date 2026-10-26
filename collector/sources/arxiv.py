"""arXiv API. 검색식 예: (abs:"co-scientist" OR abs:agentic) AND (abs:water OR abs:hydrology)"""
from __future__ import annotations

import feedparser

from collector.sources._common import get

API = "https://export.arxiv.org/api/query"


def fetch(query: str, max_results: int = 25):
    params = {
        "search_query": query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": max_results,
    }
    feed = feedparser.parse(get(API, params=params).text)
    for e in feed.entries:
        yield {
            "kind": "paper",
            "title": " ".join((e.get("title") or "").split()),
            "url": e.get("link"),
            "doi": e.get("arxiv_doi"),
            "authors": ", ".join(a.get("name", "") for a in e.get("authors", [])[:6]) or None,
            "venue": "arXiv",
            "published_at": (e.get("published") or "")[:10] or None,
            "text": e.get("summary") or "",
            "raw": {"arxiv_id": e.get("id"), "categories": [t.get("term") for t in e.get("tags", [])]},
        }
