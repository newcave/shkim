import streamlit as st

from core import content, db, ui

profile = content.load_profile()

# ── 히어로: 사진·이름·직책·논제·약력 ─────────────────────
ui.hero(profile, content.photo_path())

st.markdown("<hr class='soft-rule'>", unsafe_allow_html=True)

# ── 학력 + 경력 타임라인 ────────────────────────────────
if profile.get("education") or profile.get("career"):
    edu_col, career_col = st.columns([1, 1.7], gap="large")
    with edu_col:
        if profile.get("education"):
            st.markdown("<div class='eyebrow'>학력</div>", unsafe_allow_html=True)
            for line in profile["education"]:
                st.markdown(
                    f"<div class='tl__role' style='margin-bottom:.5rem'>{line}</div>",
                    unsafe_allow_html=True,
                )
    with career_col:
        if profile.get("career"):
            st.markdown("<div class='eyebrow'>주요 경력</div>", unsafe_allow_html=True)
            ui.career_timeline(profile["career"])

    st.markdown("<hr class='soft-rule'>", unsafe_allow_html=True)

# ── 최근 활동: 피드 · 게시글 ────────────────────────────
c1, c2 = st.columns(2, gap="large")
with c1:
    st.markdown("<div class='eyebrow'>최근 수집 자료</div>", unsafe_allow_html=True)
    items = db.feed_recent(5)
    if items:
        for it in items:
            ui.feed_line(it)
    else:
        ui.empty("아직 수집된 자료가 없습니다.", "GitHub Actions의 collect 워크플로를 한 번 실행하면 여기에 쌓입니다.")
    st.page_link("views/feed.py", label="피드 전체 보기")
with c2:
    st.markdown("<div class='eyebrow'>최근 게시글</div>", unsafe_allow_html=True)
    posts = db.posts(limit=3)
    if posts:
        for p in posts:
            st.markdown(
                f"- **{p['title']}**  \n  <span class='muted' style='font-size:.9em'>"
                f"{p.get('author_name') or '익명'} · {ui.fmt_date(p.get('created_at'))}</span>",
                unsafe_allow_html=True,
            )
    else:
        ui.empty("첫 글을 기다리고 있습니다.", "게시판에서 질문이나 제안을 남겨 주세요.")
    st.page_link("views/board.py", label="게시판 가기")

last = db.last_collected()
if last:
    st.caption(f"마지막 수집 {ui.fmt_datetime(last)}")
