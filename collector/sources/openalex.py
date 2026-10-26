"""OpenAlex 논문 검색. 키 없이 쓸 수 있고, mailto를 주면 더 빠른 풀을 쓴다."""
from __future__ import annotations

import datetime as dt

from collector.sources._common import get

API = "https://api.openalex.org/works"


def _abstract(inverted: dict | None) -> str:
    if not inverted:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in inverted.items():
        positions.extend((i, word) for i in idxs)
    return " ".join(w for _, w in sorted(positions))


def fetch(query: str, days: int = 30, email: str | None = None, per_page: int = 25):
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    params = {
        "search": query,
        "filter": f"from_publication_date:{since}",
        "sort": "publication_date:desc",
        "per-page": per_page,
    }
    if email:
        params["mailto"] = email
    data = get(API, params=params).json()
    for w in data.get("results", []):
        loc = w.get("primary_location") or {}
        doi = w.get("doi")
        url = loc.get("landing_page_url") or doi or w.get("id")
        authors = [a["author"]["display_name"] for a in w.get("authorships", [])[:6]
                   if a.get("author") and a["author"].get("display_name")]
        yield {
            "kind": "paper",
            "title": w.get("display_name") or w.get("title") or "",
            "url": url,
            "doi": doi,
            "authors": ", ".join(authors) or None,
            "venue": (loc.get("source") or {}).get("display_name"),
            "published_at": w.get("publication_date"),
            "text": _abstract(w.get("abstract_inverted_index")),
            "raw": {
                "openalex_id": w.get("id"),
                "oa_url": (w.get("open_access") or {}).get("oa_url"),
                "cited_by_count": w.get("cited_by_count"),
                "type": w.get("type"),
            },
        }
