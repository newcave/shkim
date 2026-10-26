"""데이터 계층.

앱은 이 모듈의 함수만 호출한다. 뒤에서는 Supabase(운영) 또는 메모리 샘플 데이터(데모)가 동작한다.
- DEMO_MODE = true 이거나 SUPABASE_URL/KEY가 없으면 데모 백엔드.
- Supabase에는 서버 측에서 service_role 키로 접근한다(브라우저에 노출되지 않음). RLS는 anon 전면 차단.
"""
from __future__ import annotations

import datetime as dt
import re
import uuid

import streamlit as st

from core.auth import secret

KIND_LABEL = {"paper": "논문", "news": "뉴스", "video": "영상", "report": "보고서"}
PUB_TYPE_LABEL = {
    "journal": "학술지",
    "conference": "학술대회",
    "report": "보고서",
    "talk": "발표",
    "patent": "특허",
}


def _clean_query(q: str) -> str:
    """PostgREST 필터 문법을 깨는 문자를 제거한다."""
    return re.sub(r"[,()\"'%]", " ", q or "").strip()


# ── Supabase ───────────────────────────────────────────────────

class SupabaseBackend:
    demo = False

    def __init__(self, url: str, key: str):
        from supabase import create_client

        self.c = create_client(url, key)

    # 피드
    def feed(self, q=None, kinds=None, lang=None, days=None, tags=None,
             sort="recent", limit=30, offset=0):
        qb = self.c.table("feed_items").select("*").eq("is_hidden", False)
        if kinds:
            qb = qb.in_("kind", list(kinds))
        if lang and lang != "all":
            qb = qb.eq("lang", lang)
        if days:
            since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
            qb = qb.gte("published_at", since)
        if tags:
            qb = qb.overlaps("tags", list(tags))
        q = _clean_query(q or "")
        if q:
            qb = qb.or_(f"title.ilike.%{q}%,summary_ko.ilike.%{q}%,venue.ilike.%{q}%,authors.ilike.%{q}%")
        qb = qb.order("is_pinned", desc=True)
        if sort == "score":
            qb = qb.order("score", desc=True)
        qb = qb.order("published_at", desc=True, nullsfirst=False).order("created_at", desc=True)
        return qb.range(offset, offset + limit - 1).execute().data

    def feed_recent(self, n=5):
        return self.feed(limit=n)

    def feed_tags(self, sample=300):
        rows = (self.c.table("feed_items").select("tags").eq("is_hidden", False)
                .order("created_at", desc=True).limit(sample).execute().data)
        return _count_tags(rows)

    def feed_admin(self, q=None, limit=40):
        qb = self.c.table("feed_items").select("*")
        q = _clean_query(q or "")
        if q:
            qb = qb.ilike("title", f"%{q}%")
        return qb.order("created_at", desc=True).limit(limit).execute().data

    def set_feed_item(self, item_id, **fields):
        self.c.table("feed_items").update(fields).eq("id", item_id).execute()

    def last_collected(self):
        rows = (self.c.table("feed_items").select("created_at")
                .order("created_at", desc=True).limit(1).execute().data)
        return rows[0]["created_at"] if rows else None

    # 연구·미디어
    def publications(self):
        return (self.c.table("publications").select("*")
                .order("is_featured", desc=True).order("year", desc=True).execute().data)

    def media(self):
        return (self.c.table("media").select("*")
                .order("published_at", desc=True, nullsfirst=False).execute().data)

    # 게시판
    def posts(self, status="approved", limit=50):
        return (self.c.table("posts").select("*").eq("status", status)
                .order("is_pinned", desc=True).order("created_at", desc=True)
                .limit(limit).execute().data)

    def create_post(self, post: dict):
        return self.c.table("posts").insert(post).execute().data[0]

    def set_post(self, post_id, **fields):
        self.c.table("posts").update(fields).eq("id", post_id).execute()

    # 소스
    def sources(self):
        return self.c.table("sources").select("*").order("id").execute().data

    def set_source(self, source_id, **fields):
        self.c.table("sources").update(fields).eq("id", source_id).execute()

    # harvest
    def insert_harvest(self, run: dict, items: list[dict]):
        self.c.table("harvest_runs").insert(run).execute()
        inserted = 0
        for i in range(0, len(items), 100):
            res = (self.c.table("feed_items")
                   .upsert(items[i:i + 100], on_conflict="url", ignore_duplicates=True)
                   .execute())
            inserted += len(res.data or [])
        return inserted


# ── 데모(샘플 데이터) ────────────────────────────────────────────

class DemoBackend:
    """Supabase 연결 전 화면 확인용. 프로세스가 살아 있는 동안만 데이터가 유지된다."""

    demo = True

    def __init__(self):
        today = dt.date.today()

        def d(days_ago):
            return (today - dt.timedelta(days=days_ago)).isoformat()

        self.feed_items = [
            dict(id=str(uuid.uuid4()), kind="paper", title="(샘플) 수문 예측을 위한 에이전트형 AI 프레임워크 검토",
                 url="https://example.org/sample-paper-1", doi=None, authors="A. Kim, B. Lee", venue="Sample Journal of Hydrology",
                 published_at=d(2), lang="en", summary_ko="LLM 에이전트가 수문 모델 실험을 스스로 설계·검증하는 절차를 제안한다. Water Co-Scientist의 실험 자동화 단계와 직접 연결된다.",
                 tags=["agentic-ai", "hydrology"], score=3, is_pinned=True, is_hidden=False),
            dict(id=str(uuid.uuid4()), kind="news", title="(샘플) 국내 정수장 AI 운영 확대… 약품 주입 최적화 성과",
                 url="https://example.org/sample-news-1", doi=None, authors=None, venue="샘플 매체",
                 published_at=d(3), lang="ko", summary_ko="AI 정수장 확대 적용 사례와 에너지 절감 효과를 다룬 기사.",
                 tags=["ai-water-plant"], score=1, is_pinned=False, is_hidden=False),
            dict(id=str(uuid.uuid4()), kind="video", title="(샘플) 디지털트윈으로 보는 유역 홍수 대응",
                 url="https://www.youtube.com/watch?v=xxxxxxxxxxx", doi=None, authors=None, venue="샘플 채널",
                 published_at=d(6), lang="ko", summary_ko=None, tags=["digital-twin", "flood"], score=2,
                 is_pinned=False, is_hidden=False),
            dict(id=str(uuid.uuid4()), kind="report", title="(샘플) INST-07 AI연구소 기술문서 — 물관리 LLM 적용 지침",
                 url="https://example.org/sample-report-1", doi=None, authors=None, venue="K-water AI연구소",
                 published_at=d(12), lang="ko", summary_ko=None, tags=["INST-07", "B_technical", "kwater-harvest"],
                 score=1, is_pinned=False, is_hidden=False),
            dict(id=str(uuid.uuid4()), kind="paper", title="(샘플) Foundation models for water resources: a survey",
                 url="https://example.org/sample-paper-2", doi="10.0000/sample.2", authors="C. Park et al.", venue="arXiv",
                 published_at=d(20), lang="en", summary_ko="물 분야 파운데이션 모델 연구를 데이터·과제·평가 기준으로 정리한 서베이.",
                 tags=["foundation-model"], score=2, is_pinned=False, is_hidden=False),
        ]
        for i, it in enumerate(self.feed_items):
            it["created_at"] = f"{d(i)}T06:00:00+00:00"
        self.publications_ = [
            dict(id=1, year=2024, type="journal", title="(샘플) 디지털 트윈 기반 스마트 물관리 플랫폼", authors="김성훈 외",
                 venue="샘플 학술지", doi=None, url="https://example.org/pub-1", pdf_url=None, is_featured=True, note=None),
            dict(id=2, year=2022, type="talk", title="(샘플) K-water 디지털 전환 과제", authors="김성훈",
                 venue="샘플 학술대회", doi=None, url="https://example.org/pub-2", pdf_url=None, is_featured=False, note=None),
        ]
        self.media_ = [
            dict(id=1, kind="article", title="(샘플) 물관리 AI 전환 인터뷰", url="https://example.org/article-1",
                 outlet="샘플 신문", published_at=d(30), note=None),
            dict(id=2, kind="video", title="(샘플) 발표 영상", url="https://static.streamlit.io/examples/star.mp4",
                 outlet="샘플 채널", published_at=d(60), note=None),
        ]
        self.posts_ = [
            dict(id=str(uuid.uuid4()), author_name="방문자 A", author_org="샘플 대학", author_email="a@example.com",
                 is_verified=True, title="(샘플) 피드 키워드 제안", body="agentic AI 외에 'physics-informed' 키워드도 넣으면 좋겠습니다.",
                 status="approved", is_pinned=False, created_at=f"{d(1)}T09:00:00+00:00"),
            dict(id=str(uuid.uuid4()), author_name="방문자 B", author_org=None, author_email=None,
                 is_verified=False, title="(샘플) 승인 대기 글", body="이름만 입력해 올린 글은 관리자가 확인한 뒤 게시됩니다.",
                 status="pending", is_pinned=False, created_at=f"{d(0)}T10:00:00+00:00"),
        ]
        self.sources_ = [
            dict(id=1, kind="paper", name="OpenAlex — co-scientist × water", method="openalex",
                 query='("co-scientist" OR "agentic AI") AND (water OR hydrology)', lang="en", weight=1.5, active=True),
            dict(id=2, kind="news", name="구글뉴스 — 물관리 AI", method="gnews_rss",
                 query='물관리 AI OR "AI 정수장"', lang="ko", weight=1.0, active=True),
        ]

    def feed(self, q=None, kinds=None, lang=None, days=None, tags=None, sort="recent", limit=30, offset=0):
        rows = [r for r in self.feed_items if not r["is_hidden"]]
        if kinds:
            rows = [r for r in rows if r["kind"] in kinds]
        if lang and lang != "all":
            rows = [r for r in rows if r["lang"] == lang]
        if days:
            since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
            rows = [r for r in rows if (r["published_at"] or "") >= since]
        if tags:
            rows = [r for r in rows if set(r["tags"]) & set(tags)]
        if q:
            ql = q.lower()
            rows = [r for r in rows if ql in " ".join(
                str(r.get(k) or "") for k in ("title", "summary_ko", "venue", "authors")).lower()]
        key = (lambda r: (r["is_pinned"], r["score"], r["published_at"] or "")) if sort == "score" \
            else (lambda r: (r["is_pinned"], r["published_at"] or ""))
        rows = sorted(rows, key=key, reverse=True)
        return rows[offset:offset + limit]

    def feed_recent(self, n=5):
        return self.feed(limit=n)

    def feed_tags(self, sample=300):
        return _count_tags(self.feed_items)

    def feed_admin(self, q=None, limit=40):
        rows = self.feed_items
        if q:
            rows = [r for r in rows if q.lower() in r["title"].lower()]
        return rows[:limit]

    def set_feed_item(self, item_id, **fields):
        for r in self.feed_items:
            if r["id"] == item_id:
                r.update(fields)

    def last_collected(self):
        return max((r["created_at"] for r in self.feed_items), default=None)

    def publications(self):
        return sorted(self.publications_, key=lambda r: (r["is_featured"], r["year"]), reverse=True)

    def media(self):
        return sorted(self.media_, key=lambda r: r["published_at"] or "", reverse=True)

    def posts(self, status="approved", limit=50):
        rows = [p for p in self.posts_ if p["status"] == status]
        return sorted(rows, key=lambda p: (p["is_pinned"], p["created_at"]), reverse=True)[:limit]

    def create_post(self, post: dict):
        post = dict(post, id=str(uuid.uuid4()), is_pinned=False,
                    created_at=dt.datetime.now(dt.timezone.utc).isoformat())
        self.posts_.append(post)
        return post

    def set_post(self, post_id, **fields):
        for p in self.posts_:
            if p["id"] == post_id:
                p.update(fields)

    def sources(self):
        return self.sources_

    def set_source(self, source_id, **fields):
        for s in self.sources_:
            if s["id"] == source_id:
                s.update(fields)

    def insert_harvest(self, run: dict, items: list[dict]):
        known = {r["url"] for r in self.feed_items}
        new = [dict(it, id=str(uuid.uuid4()), created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                    is_pinned=False, is_hidden=False, summary_ko=None, score=it.get("score", 0))
               for it in items if it["url"] not in known]
        self.feed_items = new + self.feed_items
        return len(new)


def _count_tags(rows):
    counts: dict[str, int] = {}
    for r in rows:
        for t in r.get("tags") or []:
            counts[t] = counts.get(t, 0) + 1
    return sorted(counts.items(), key=lambda kv: kv[1], reverse=True)


# ── 백엔드 선택과 공개 함수 ──────────────────────────────────────

@st.cache_resource(show_spinner=False)
def _backend():
    url, key = secret("SUPABASE_URL"), secret("SUPABASE_SERVICE_KEY")
    if secret("DEMO_MODE") or not (url and key):
        return DemoBackend()
    return SupabaseBackend(str(url), str(key))


def is_demo() -> bool:
    return _backend().demo


def feed(**kw):
    return _backend().feed(**kw)


def feed_recent(n=5):
    return _backend().feed_recent(n)


def feed_tags(sample=300):
    return _backend().feed_tags(sample)


def feed_admin(q=None, limit=40):
    return _backend().feed_admin(q, limit)


def set_feed_item(item_id, **fields):
    return _backend().set_feed_item(item_id, **fields)


def last_collected():
    return _backend().last_collected()


def publications():
    return _backend().publications()


def media():
    return _backend().media()


def posts(status="approved", limit=50):
    return _backend().posts(status, limit)


def create_post(post: dict):
    return _backend().create_post(post)


def set_post(post_id, **fields):
    return _backend().set_post(post_id, **fields)


def sources():
    return _backend().sources()


def set_source(source_id, **fields):
    return _backend().set_source(source_id, **fields)


def insert_harvest(run: dict, items: list[dict]):
    return _backend().insert_harvest(run, items)
