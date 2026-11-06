"""수집기용 Supabase 접근. 환경변수 SUPABASE_URL, SUPABASE_SERVICE_KEY(, SUPABASE_SCHEMA)를 쓴다.
SUPABASE_SCHEMA를 비우면 public(supabase.com 프로젝트 그대로). 연구소 서버는 shkim (supabase/institute/README.md)."""
from __future__ import annotations

import os


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def make_client(url: str, key: str, schema: str | None = None):
    """schema가 public이 아니면 PostgREST에 그 스키마로 묻는다 (Accept-/Content-Profile 머리글)."""
    from supabase import create_client

    schema = (schema or "").strip() or "public"
    if schema == "public":
        return create_client(url, key)
    try:
        from supabase import ClientOptions
    except ImportError:  # 오래된 supabase-py
        from supabase.lib.client_options import ClientOptions
    return create_client(url, key, options=ClientOptions(schema=schema))


class Store:
    def __init__(self, url: str, key: str, schema: str | None = None):
        self.c = make_client(url, key, schema)

    @classmethod
    def from_env(cls) -> "Store":
        url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY")
        if not url or not key:
            raise SystemExit("SUPABASE_URL, SUPABASE_SERVICE_KEY 환경변수가 필요합니다.")
        return cls(url, key, os.environ.get("SUPABASE_SCHEMA"))

    def active_sources(self) -> list[dict]:
        return self.c.table("sources").select("*").eq("active", True).order("id").execute().data

    def recent_titles(self, n: int = 600) -> list[str]:
        rows = (self.c.table("feed_items").select("title")
                .order("created_at", desc=True).limit(n).execute().data)
        return [r["title"] for r in rows]

    def existing_dois(self, dois: list[str]) -> set[str]:
        found: set[str] = set()
        for chunk in _chunks(sorted(set(dois)), 100):
            rows = self.c.table("feed_items").select("doi").in_("doi", chunk).execute().data
            found |= {r["doi"] for r in rows if r.get("doi")}
        return found

    def insert_items(self, rows: list[dict]) -> list[dict]:
        """URL이 이미 있으면 건너뛰고, 새로 들어간 행만 돌려준다."""
        inserted: list[dict] = []
        for chunk in _chunks(rows, 100):
            res = (self.c.table("feed_items")
                   .upsert(chunk, on_conflict="url", ignore_duplicates=True)
                   .execute())
            inserted.extend(res.data or [])
        return inserted

    def set_summary(self, item_id: str, summary: str) -> None:
        self.c.table("feed_items").update({"summary_ko": summary}).eq("id", item_id).execute()

    def insert_harvest(self, run: dict, items: list[dict]) -> int:
        self.c.table("harvest_runs").insert(run).execute()
        return len(self.insert_items(items))
