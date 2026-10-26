"""화면 공통 요소. 커스텀 CSS는 이 파일의 한 블록이 전부다."""
from __future__ import annotations

import base64
import datetime as dt
import html
import re
from pathlib import Path

import streamlit as st

from core.db import KIND_LABEL

_STYLE = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css');

:root {
  --ink: #152230;        /* 본문 */
  --ink-soft: #5a6b7a;   /* 보조 텍스트 */
  --water: #0f6d84;      /* 단일 강조색 — 깊은 물빛 */
  --water-deep: #0a4d5e;
  --line: #e2e8ec;       /* 가는 구분선 */
  --wash: #f4f8f9;       /* 아주 옅은 바탕 */
}

.stApp, .stApp * {
  font-family: "Pretendard Variable", Pretendard, -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo",
               "Noto Sans KR", "Segoe UI", sans-serif;
}
.stApp code, .stApp pre, .stApp kbd { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.block-container { max-width: 1060px; padding-top: 2rem; }
h1, h2, h3 { letter-spacing: -0.015em; color: var(--ink); }
a { color: var(--water); }

/* ── 히어로 ─────────────────────────────── */
.hero { display: flex; gap: 2.2rem; align-items: flex-start; margin: .3rem 0 .4rem; }
.hero__photo { flex: 0 0 168px; }
.hero__photo img {
  width: 168px; height: 210px; object-fit: cover; border-radius: 10px;
  box-shadow: 0 1px 0 var(--line), 0 10px 28px -18px rgba(15,109,132,.5);
}
.hero__body { flex: 1 1 auto; min-width: 0; padding-top: .2rem; }
.hero__name { font-size: 2.35rem; font-weight: 800; line-height: 1.08; color: var(--ink); }
.hero__name small { font-size: 1rem; font-weight: 500; color: var(--ink-soft); margin-left: .55rem; letter-spacing: .01em; }
.hero__role { margin-top: .5rem; font-size: 1.02rem; color: var(--ink); }
.hero__role b { color: var(--water-deep); font-weight: 700; }
.hero__thesis {
  margin-top: 1rem; font-size: 1.28rem; font-weight: 600; line-height: 1.5;
  color: var(--ink); max-width: 46ch;
  border-left: 3px solid var(--water); padding-left: .9rem;
}
.hero__bio { margin-top: 1rem; color: var(--ink-soft); line-height: 1.75; max-width: 66ch; }
.hero__links { margin-top: 1rem; display: flex; flex-wrap: wrap; gap: .5rem; }
.hero__links a {
  font-size: .9rem; text-decoration: none; color: var(--water-deep);
  border: 1px solid var(--line); border-radius: 999px; padding: .28rem .8rem; background: #fff;
}
.hero__links a:hover { border-color: var(--water); background: var(--wash); }
.hero__tags { margin-top: .85rem; font-size: .88rem; color: var(--ink-soft); }

/* ── 경력 타임라인 (진짜 연대순이므로 타임라인이 맞다) ─ */
.tl { position: relative; margin: .2rem 0 0; padding-left: 1.3rem; }
.tl::before { content: ""; position: absolute; left: 4px; top: .4rem; bottom: .4rem; width: 2px; background: var(--line); }
.tl__item { position: relative; padding: 0 0 1.05rem; }
.tl__item::before {
  content: ""; position: absolute; left: -1.3rem; top: .42rem; width: 9px; height: 9px;
  border-radius: 50%; background: #fff; border: 2px solid var(--water);
}
.tl__item--now::before { background: var(--water); box-shadow: 0 0 0 3px rgba(15,109,132,.16); }
.tl__span { font-size: .8rem; font-weight: 600; color: var(--water-deep); letter-spacing: .02em; }
.tl__role { color: var(--ink); line-height: 1.5; }
.tl__role .sub { color: var(--ink-soft); }

.eyebrow { font-size: .82rem; font-weight: 700; color: var(--water-deep); margin: 0 0 .5rem; }
.soft-rule { height: 1px; background: var(--line); border: 0; margin: 1.8rem 0; }
.muted { color: var(--ink-soft); }
</style>
"""


def inject_style() -> None:
    st.markdown(_STYLE, unsafe_allow_html=True)


def page_header(title: str, desc: str | None = None) -> None:
    st.markdown(f"## {title}")
    if desc:
        st.caption(desc)


def _esc(s) -> str:
    return html.escape(str(s or ""))


@st.cache_data(show_spinner=False)
def _photo_data_uri(path_str: str, mtime: float) -> str:
    """사진을 data URI로. mtime을 인자로 받아 파일이 바뀌면 캐시가 갱신된다."""
    data = Path(path_str).read_bytes()
    ext = Path(path_str).suffix.lower().lstrip(".") or "jpeg"
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    return f"data:image/{mime};base64,{base64.b64encode(data).decode()}"


def hero(profile: dict, photo_path: Path | None) -> None:
    """홈 상단 히어로. 사진·이름·직책·논제·약력·링크를 한 덩어리로 그린다."""
    name = _esc(profile.get("name"))
    name_en = f"<small>{_esc(profile['name_en'])}</small>" if profile.get("name_en") else ""

    role_bits = [b for b in [profile.get("title"), profile.get("affiliation")] if b]
    role_html = ""
    if role_bits:
        role_html = "<div class='hero__role'><b>" + _esc(role_bits[0]) + "</b>"
        if len(role_bits) > 1:
            role_html += " · " + _esc(role_bits[1])
        if profile.get("location"):
            role_html += " · " + _esc(profile["location"])
        role_html += "</div>"

    thesis = f"<div class='hero__thesis'>{_esc(profile['one_liner'])}</div>" if profile.get("one_liner") else ""
    bio = f"<div class='hero__bio'>{_esc(profile['bio']).strip()}</div>" if profile.get("bio") else ""

    links = ""
    chips = [l for l in (profile.get("links") or []) if l.get("url")]
    if chips:
        links = "<div class='hero__links'>" + "".join(
            f"<a href='{_esc(l['url'])}' target='_blank' rel='noopener'>{_esc(l['label'])}</a>" for l in chips
        ) + "</div>"

    tags = ""
    if profile.get("interests"):
        tags = "<div class='hero__tags'>관심 분야 — " + _esc(" / ".join(profile["interests"])) + "</div>"

    photo_html = ""
    if photo_path and Path(photo_path).exists():
        uri = _photo_data_uri(str(photo_path), Path(photo_path).stat().st_mtime)
        photo_html = f"<div class='hero__photo'><img src='{uri}' alt='{name}'></div>"

    st.markdown(
        f"<div class='hero'>{photo_html}"
        f"<div class='hero__body'><div class='hero__name'>{name}{name_en}</div>"
        f"{role_html}{thesis}{bio}{links}{tags}</div></div>",
        unsafe_allow_html=True,
    )


_NOW_RE = re.compile(r"현재\s*\)?\s*$")


def career_timeline(items: list[str]) -> None:
    """'역할 (2010~현재)' 형태의 경력 문자열을 연대 타임라인으로 그린다."""
    rows = []
    for raw in items:
        s = str(raw).strip()
        m = re.search(r"\(([^()]*)\)\s*$", s)
        span = m.group(1).strip() if m else ""
        role = (s[: m.start()].strip() if m else s)
        now = bool(_NOW_RE.search(span))
        # '역할 · 보조설명' 분리
        if " · " in role:
            head, sub = role.split(" · ", 1)
            role_html = f"{_esc(head)} <span class='sub'>· {_esc(sub)}</span>"
        else:
            role_html = _esc(role)
        rows.append(
            f"<div class='tl__item{' tl__item--now' if now else ''}'>"
            f"<div class='tl__span'>{_esc(span) or '—'}</div>"
            f"<div class='tl__role'>{role_html}</div></div>"
        )
    st.markdown(f"<div class='tl'>{''.join(rows)}</div>", unsafe_allow_html=True)


def empty(message: str, hint: str | None = None) -> None:
    """비어 있는 화면은 다음 행동을 안내한다."""
    with st.container(border=True):
        st.write(message)
        if hint:
            st.caption(hint)


def fmt_date(value) -> str:
    if not value:
        return ""
    s = str(value)
    return s[:10]


def fmt_datetime(value) -> str:
    if not value:
        return ""
    try:
        t = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        t = t.astimezone(dt.timezone(dt.timedelta(hours=9)))
        return t.strftime("%Y-%m-%d %H:%M KST")
    except ValueError:
        return str(value)[:16]


def feed_card(item: dict, compact: bool = False) -> None:
    kind = KIND_LABEL.get(item.get("kind"), item.get("kind") or "")
    meta = " · ".join(x for x in [kind, item.get("venue"), fmt_date(item.get("published_at")),
                                  {"ko": "한국어", "en": "영어"}.get(item.get("lang"), None)] if x)
    with st.container(border=True):
        title = item.get("title") or "(제목 없음)"
        prefix = "고정 · " if item.get("is_pinned") else ""
        st.markdown(f"**{prefix}[{title}]({item.get('url')})**")
        if meta:
            st.caption(meta)
        if not compact:
            if item.get("authors"):
                st.caption(item["authors"])
            if item.get("summary_ko"):
                st.write(item["summary_ko"])
            if item.get("tags"):
                st.caption("  ".join(f"#{t}" for t in item["tags"]))


def feed_line(item: dict) -> None:
    """홈에서 쓰는 한 줄 표기."""
    meta = " · ".join(x for x in [KIND_LABEL.get(item.get("kind")), item.get("venue"),
                                  fmt_date(item.get("published_at"))] if x)
    st.markdown(f"- [{item.get('title')}]({item.get('url')})  \n  <span style='opacity:.65;font-size:.9em'>{meta}</span>",
                unsafe_allow_html=True)


def post_card(post: dict, actions=None) -> None:
    """게시글 카드. actions는 관리 페이지에서 버튼을 그리는 콜백."""
    with st.container(border=True):
        badge = " :blue-background[인증]" if post.get("is_verified") else ""
        pin = "고정 · " if post.get("is_pinned") else ""
        st.markdown(f"**{pin}{post.get('title')}**{badge}")
        who = post.get("author_name") or "익명"
        if post.get("author_org"):
            who += f" · {post['author_org']}"
        st.caption(f"{who} · {fmt_datetime(post.get('created_at'))}")
        st.write(post.get("body") or "")
        if actions:
            actions(post)
