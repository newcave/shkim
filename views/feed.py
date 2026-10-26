import streamlit as st

from core import db, ui
from core.db import KIND_LABEL

PAGE = 20
PERIODS = {"전체": None, "최근 7일": 7, "최근 30일": 30, "최근 90일": 90, "최근 1년": 365}

ui.page_header("Co-Scientist 피드", "Water Co-Scientist 관련 논문·뉴스·영상·보고서를 매일 자동으로 모읍니다.")

q = st.text_input("검색", placeholder="제목, 요약, 출처, 저자에서 찾기", label_visibility="collapsed")
c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
with c1:
    kinds = st.pills("종류", list(KIND_LABEL), selection_mode="multi", format_func=lambda k: KIND_LABEL[k])
with c2:
    lang = st.segmented_control("언어", ["all", "ko", "en"], default="all",
                                format_func=lambda v: {"all": "전체", "ko": "한국어", "en": "영어"}[v]) or "all"
with c3:
    period = st.selectbox("기간", list(PERIODS), index=0)
with c4:
    sort = st.segmented_control("정렬", ["recent", "score"], default="recent",
                                format_func=lambda v: {"recent": "최신순", "score": "관련도순"}[v]) or "recent"

top_tags = [t for t, _ in db.feed_tags()[:12]]
tags = st.pills("태그", top_tags, selection_mode="multi") if top_tags else []

# 조건이 바뀌면 페이지 수를 처음으로 되돌린다.
signature = (q, tuple(kinds or []), lang, period, sort, tuple(tags or []))
if st.session_state.get("feed_sig") != signature:
    st.session_state["feed_sig"] = signature
    st.session_state["feed_limit"] = PAGE

limit = st.session_state.get("feed_limit", PAGE)
items = db.feed(q=q, kinds=kinds, lang=lang, days=PERIODS[period], tags=tags, sort=sort, limit=limit + 1)

if not items:
    if any([q, kinds, lang != "all", PERIODS[period], tags]):
        ui.empty("조건에 맞는 자료가 없습니다.", "검색어나 필터를 줄여 보세요.")
    else:
        ui.empty("아직 수집된 자료가 없습니다.", "GitHub Actions의 collect 워크플로를 실행하면 매일 자동으로 쌓입니다.")
    st.stop()

has_more = len(items) > limit
for it in items[:limit]:
    ui.feed_card(it)

if has_more:
    if st.button(f"더 보기 ({PAGE}건)", width="stretch"):
        st.session_state["feed_limit"] = limit + PAGE
        st.rerun()
else:
    st.caption("끝까지 봤습니다.")
