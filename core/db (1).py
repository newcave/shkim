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

        # 아래 피드 항목은 실제 공개 논문·기사로 채워져 있다(2026-10 검색). 정리·취사선택은 운영자가.
        self.feed_items = [
            dict(id=str(uuid.uuid4()), kind="paper",
                 title="HydroAgent: Closing the Gap Between Frontier LLMs and Human Experts in Hydrologic Model Calibration via Simulator-Grounded RL",
                 url="https://arxiv.org/abs/2605.17792", doi=None,
                 authors="Zhi Li, Songkun Yan, Jie Cao, Mofan Zhang, Anjiang Wei, Jinwoong Yoo, Yang Hong",
                 venue="arXiv (cs.LG)", published_at="2026-05-18", lang="en",
                 summary_ko="최신 LLM 에이전트도 CREST 수문모형 보정에서 전문가에 못 미친다는 점을 보이고, 시뮬레이터 피드백을 보상으로 쓰는 소형 모델(HydroAgent)을 제안한다. Water Co-Scientist의 '자동 보정' 단계와 직접 맞닿는다.",
                 tags=["agentic-ai", "llm", "hydrology"], score=5, is_pinned=True, is_hidden=False),
            dict(id=str(uuid.uuid4()), kind="paper",
                 title="AQUAH: Automatic Quantification and Unified Agent in Hydrology",
                 url="https://arxiv.org/abs/2508.02936", doi=None,
                 authors="Songkun Yan, Zhi Li, Siyu Zhu, Yixin Wen, Mofan Zhang, Mengye Chen, Jie Cao, Yang Hong",
                 venue="arXiv / ICCV 2025 Workshop", published_at="2025-08-04", lang="en",
                 summary_ko="자연어 요청만으로 지형·기상·유량 데이터를 모아 수문 모형을 설정·실행하고 보고서까지 내는 언어모델 에이전트. 'co-scientist'형 자동화의 대표 사례다.",
                 tags=["agentic-ai", "llm", "hydrology"], score=4, is_pinned=True, is_hidden=False),
            dict(id=str(uuid.uuid4()), kind="paper",
                 title="WaterCopilot: An AI-Driven Virtual Assistant for Water Management",
                 url="https://arxiv.org/abs/2601.08559", doi=None,
                 authors="Keerththanan Vickneswaran, Chris Dickens, Mariangel Garcia Andarcia, Paulo Silva, Hugo Retief",
                 venue="arXiv", published_at="2026-01-14", lang="en",
                 summary_ko="정책 문서와 실시간 수문 DB를 검색해 출처와 함께 답하는 유역 관리용 RAG 챗봇(림포포강). 운영 현장용 어시스턴트 설계의 참고점.",
                 tags=["llm", "water-management", "smart-water"], score=3, is_pinned=False, is_hidden=False),
            dict(id=str(uuid.uuid4()), kind="paper",
                 title="Unlocking the Potential: Benchmarking Large Language Models in Water Engineering and Research",
                 url="https://arxiv.org/abs/2407.21045", doi=None,
                 authors="Boyan Xu, Liang Wen, Zihao Li, et al.",
                 venue="arXiv", published_at="2024-07-30", lang="en",
                 summary_ko="물 공학·연구 과제 983개로 7개 LLM을 평가한 벤치마크(WaterER). 물 분야 전문 모델이 되려면 도메인 파인튜닝이 필요함을 보인다.",
                 tags=["llm", "water-management"], score=3, is_pinned=False, is_hidden=False),
            dict(id=str(uuid.uuid4()), kind="paper",
                 title="Foundation Models for Environmental Science: A Survey of Emerging Frontiers",
                 url="https://arxiv.org/abs/2504.04280", doi=None,
                 authors="(survey)", venue="arXiv", published_at="2025-04-05", lang="en",
                 summary_ko="기상·수문·환경을 아우르는 파운데이션 모델 연구를 데이터·과제·평가 축으로 정리한 서베이. 물 분야 기반모델의 큰 그림을 잡기 좋다.",
                 tags=["foundation-model", "hydrology"], score=2, is_pinned=False, is_hidden=False),
            dict(id=str(uuid.uuid4()), kind="news",
                 title="K-water, OpenAI와 AI 기반 기후·물관리 기술 개발 협력",
                 url="https://koreatimes.co.kr/southkorea/society/20260527/k-water-partners-with-openai-on-ai-driven-climate-water-management",
                 doi=None, authors=None, venue="The Korea Times", published_at="2026-05-27", lang="en",
                 summary_ko="K-water가 OpenAI와 물 특화 LLM·기후 예측·AI 정수장 모델 개발에 협력하기로 했다. 물 분야 거대모델 개발의 국내 최전선 움직임.",
                 tags=["k-water", "llm", "ai-water-plant"], score=3, is_pinned=False, is_hidden=False),
            dict(id=str(uuid.uuid4()), kind="news",
                 title="K-water, UN HELP 총회서 디지털트윈·AI 물관리 기술 공개",
                 url="https://www.fnnews.com/news/202605061522364426", doi=None, authors=None,
                 venue="파이낸셜뉴스", published_at="2026-05-06", lang="ko",
                 summary_ko="디지털 가람+(Digital GARAM+), AI 정수처리, 스마트 물 네트워크를 3대 초격차 기술로 소개한 기술보고서 발간 소식.",
                 tags=["k-water", "digital-twin", "ai-water-plant"], score=2, is_pinned=False, is_hidden=False),
            dict(id=str(uuid.uuid4()), kind="news",
                 title="K-water, 베트남 켄동 정수장에 AI 정수장 운영기술 수출",
                 url="https://www.fnnews.com/news/202604121804439096", doi=None, authors=None,
                 venue="파이낸셜뉴스", published_at="2026-04-12", lang="ko",
                 summary_ko="화성정수장 AI 운영 노하우를 베트남 호찌민 켄동 정수장에 수출. AI 정수장 기술의 첫 해외 상용화 사례.",
                 tags=["k-water", "ai-water-plant"], score=2, is_pinned=False, is_hidden=False),
        ]
        for i, it in enumerate(self.feed_items):
            it["created_at"] = f"{d(i)}T06:00:00+00:00"
        # 연구·발표는 본인 확인이 필요하므로 자리표시자 1건만 둔다. 실제 목록을 주면 교체.
        self.publications_ = [
            dict(id=1, year=2025, type="talk", title="(입력 대기) 발표·논문 제목", authors="김성훈 외",
                 venue="학술대회/학술지", doi=None, url=None, pdf_url=None, is_featured=False,
                 note="실제 발표·논문 목록을 알려주시면 이 표를 채웁니다."),
        ]
        # 미디어는 공개 기사로 채움(2026-10 검색). K-water AI 관련 보도.
        self.media_ = [
            dict(id=1, kind="article", title="K-water, OpenAI와 AI 기반 기후·물관리 기술 개발 협력",
                 url="https://koreatimes.co.kr/southkorea/society/20260527/k-water-partners-with-openai-on-ai-driven-climate-water-management",
                 outlet="The Korea Times", published_at="2026-05-27", note=None),
            dict(id=2, kind="article", title="한강 '디지털 트윈'으로 관리… '디지털 가람플러스' 5대강 확대",
                 url="https://www.smarttoday.co.kr/ko-kr/articles/24169",
                 outlet="스마트투데이", published_at="2026-07-15", note=None),
            dict(id=3, kind="article", title="K-water, 베트남 켄동 정수장에 AI 정수장 운영기술 수출",
                 url="https://www.fnnews.com/news/202604121804439096",
                 outlet="파이낸셜뉴스", published_at="2026-04-12", note=None),
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
