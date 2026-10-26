"""매일 실행되는 수집기.

    python -m collector.collect

환경변수: SUPABASE_URL, SUPABASE_SERVICE_KEY (필수), OPENALEX_EMAIL, LOOKBACK_DAYS(기본 14),
          SUMMARIZE=1 + ANTHROPIC_API_KEY (선택 요약)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import traceback

from collector import normalize as nz
from collector import summarize
from collector.sources import arxiv, gnews, openalex, rss, youtube
from collector.store import Store


def fetch_for(source: dict, days: int):
    method, query = source["method"], (source.get("query") or "").strip()
    if method == "openalex":
        return openalex.fetch(query, days=days, email=os.environ.get("OPENALEX_EMAIL"))
    if method == "arxiv":
        return arxiv.fetch(query)
    if method == "gnews_rss":
        return gnews.fetch(query, lang=source.get("lang") or "ko", days=days)
    if method == "rss":
        return rss.fetch(query, kind=source.get("kind") or "news")
    if method == "youtube_rss":
        cfg = json.loads(query) if query.startswith("{") else {"channel_id": query}
        return youtube.fetch(cfg["channel_id"], cfg.get("keywords"))
    raise ValueError(f"알 수 없는 method: {method}")


def to_row(source: dict, item: dict, since: str) -> tuple[dict, str] | None:
    """소스 항목을 DB 행으로. 기준에 못 미치면 None."""
    url = nz.normalize_url(item.get("url"))
    title = " ".join((item.get("title") or "").split())
    if not url or len(title) < 8:
        return None
    published = item.get("published_at")
    if published and published < since:
        return None
    text = nz.clean_text(item.get("text"))
    tags, score = nz.tag_and_score(f"{title} {text}", source.get("weight") or 1.0)
    row = {
        "source_id": source["id"],
        "kind": item.get("kind") or source.get("kind") or "news",
        "title": title[:300],
        "url": url,
        "doi": nz.normalize_doi(item.get("doi")),
        "authors": (item.get("authors") or None) and item["authors"][:300],
        "venue": (item.get("venue") or None) and item["venue"][:120],
        "published_at": published,
        "lang": nz.detect_lang(f"{title} {text[:500]}"),
        "tags": tags,
        "score": score,
        "raw": item.get("raw") or {},
    }
    return row, text


def main() -> int:
    days = int(os.environ.get("LOOKBACK_DAYS", "14"))
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    store = Store.from_env()
    sources = store.active_sources()
    print(f"[collect] {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC · 소스 {len(sources)}개 · 최근 {days}일")

    known_keys = [nz.title_key(t) for t in store.recent_titles()]
    rows: dict[str, dict] = {}
    texts: dict[str, str] = {}
    seen_dois: set[str] = set()
    per_source: dict[str, int] = {}

    for s in sources:
        name = s.get("name") or f"#{s['id']}"
        try:
            items = list(fetch_for(s, days))
        except Exception as e:
            print(f"  ✗ {name}: {type(e).__name__}: {e}")
            continue
        added = 0
        for it in items:
            conv = to_row(s, it, since)
            if not conv:
                continue
            row, text = conv
            if row["url"] in rows or nz.is_near_duplicate(row["title"], known_keys):
                continue
            if row["doi"]:
                if row["doi"] in seen_dois:
                    continue
                seen_dois.add(row["doi"])
            rows[row["url"]] = row
            texts[row["url"]] = text
            known_keys.append(nz.title_key(row["title"]))
            added += 1
        per_source[name] = added
        print(f"  ✓ {name}: 후보 {len(items)}건 → 신규 후보 {added}건")

    # DB에 이미 있는 DOI(다른 URL로 들어온 같은 논문)는 제외
    if seen_dois:
        for doi in store.existing_dois(list(seen_dois)):
            for url in [u for u, r in rows.items() if r["doi"] == doi]:
                rows.pop(url, None)

    if not rows:
        print("[collect] 새 항목 없음")
        return 0

    inserted = store.insert_items(list(rows.values()))
    print(f"[collect] {len(rows)}건 시도 → {len(inserted)}건 추가 (URL 중복 {len(rows) - len(inserted)}건 건너뜀)")

    n = summarize.summarize_new(store, inserted, texts)
    if n:
        print(f"[collect] 요약 {n}건")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        sys.exit(1)
