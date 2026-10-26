"""사이드바 유튜브 모듈.

구성: 상단에 고정 추천 영상(수동 지정) + 그 아래 채널 최신 영상 자동.
채널 ID나 추천 영상이 없으면 안내만 조용히 띄우고, 네트워크 실패도 사이드바를 깨지 않는다.

설정은 content/youtube.yaml 에서 읽는다:
    channel_id: "UCxxxx..."          # 최신 영상을 끌어올 채널 (없으면 자동 목록 생략)
    channel_url: "https://..."       # '채널 보기' 링크 (선택)
    max_latest: 3                    # 최신 영상 개수
    featured:                        # 상단 고정 추천 (선택)
      - url: "https://www.youtube.com/watch?v=..."
        title: "영상 제목"
"""
from __future__ import annotations

import re
from pathlib import Path

import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "content" / "youtube.yaml"

_YT_ID = re.compile(r"(?:v=|youtu\.be/|/shorts/|/embed/)([\w-]{11})")
FEED = "https://www.youtube.com/feeds/videos.xml"


def _config() -> dict:
    # 캐시하지 않는다 — youtube.yaml이 바뀌면 즉시 반영되도록.
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _video_id(url: str) -> str | None:
    m = _YT_ID.search(url or "")
    return m.group(1) if m else None


@st.cache_data(ttl=3600, show_spinner=False)
def _latest(channel_id: str, n: int) -> list[dict]:
    """채널 RSS에서 최신 영상 n개. 실패하면 빈 목록."""
    try:
        import feedparser
        import requests

        r = requests.get(FEED, params={"channel_id": channel_id}, timeout=15,
                         headers={"User-Agent": "shkim-page/1.0"})
        r.raise_for_status()
        feed = feedparser.parse(r.content)
        out = []
        for e in feed.entries[:n]:
            vid = e.get("yt_videoid") or _video_id(e.get("link", ""))
            if vid:
                out.append({"id": vid, "title": e.get("title", ""), "url": e.get("link")})
        return out
    except Exception:
        return []


def render() -> None:
    """사이드바에 유튜브 블록을 그린다. app.py에서 네비게이션 아래에 호출."""
    cfg = _config()
    featured = cfg.get("featured") or []
    channel_id = (cfg.get("channel_id") or "").strip()

    with st.sidebar:
        st.divider()
        st.markdown("###### 관련 영상")

        shown = 0
        for f in featured:
            vid = _video_id(f.get("url", ""))
            if not vid:
                continue
            st.video(f"https://www.youtube.com/watch?v={vid}")
            if f.get("title"):
                st.caption(f["title"])
            shown += 1

        if channel_id and not channel_id.startswith("UCxxxx"):
            for v in _latest(channel_id, int(cfg.get("max_latest", 3))):
                if any(_video_id(f.get("url", "")) == v["id"] for f in featured):
                    continue  # 추천과 중복 제거
                st.video(v["url"])
                if v.get("title"):
                    st.caption(v["title"])
                shown += 1

        if shown == 0:
            st.caption("영상을 준비 중입니다. content/youtube.yaml에 채널 ID나 추천 영상을 넣으면 여기에 표시됩니다.")

        if cfg.get("channel_url"):
            st.markdown(f"[유튜브 채널 보기 →]({cfg['channel_url']})")

        links = cfg.get("links") or []
        if links:
            st.markdown("###### 주요 자료")
            for l in links:
                if l.get("url") and l.get("label"):
                    st.markdown(f"- [{l['label']}]({l['url']})")
