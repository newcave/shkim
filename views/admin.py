import pandas as pd
import streamlit as st

from core import auth, db, ui
from scripts.import_harvest import parse_index, to_feed_items, to_run

if not auth.is_admin():
    st.error("관리자만 볼 수 있는 페이지입니다.")
    st.stop()

ui.page_header("관리", "게시글 승인, 피드 정리, 수집 소스, harvest 인덱스 반영.")

tab_posts, tab_feed, tab_sources, tab_harvest = st.tabs(["대기 글", "피드 관리", "수집 소스", "harvest 반영"])

# ── 대기 글 ─────────────────────────────────────────────────────
with tab_posts:
    pending = db.posts(status="pending")
    if not pending:
        ui.empty("승인을 기다리는 글이 없습니다.")
    else:
        st.caption(f"{len(pending)}건")

        def _actions(p):
            b1, b2, _ = st.columns([1, 1, 6])
            if b1.button("게시", key=f"ok_{p['id']}", type="primary"):
                db.set_post(p["id"], status="approved")
                st.rerun()
            if b2.button("숨김", key=f"hide_{p['id']}"):
                db.set_post(p["id"], status="hidden")
                st.rerun()

        for p in pending:
            ui.post_card(p, actions=_actions)

    st.markdown("#### 게시된 글")
    approved = db.posts(status="approved", limit=20)
    for p in approved:
        with st.container(border=True):
            c1, c2, c3 = st.columns([6, 1, 1])
            c1.markdown(f"**{p['title']}** — {p.get('author_name')} · {ui.fmt_datetime(p.get('created_at'))}")
            if c2.button("고정 해제" if p.get("is_pinned") else "고정", key=f"pin_{p['id']}"):
                db.set_post(p["id"], is_pinned=not p.get("is_pinned"))
                st.rerun()
            if c3.button("숨김", key=f"hide2_{p['id']}"):
                db.set_post(p["id"], status="hidden")
                st.rerun()

# ── 피드 관리 ────────────────────────────────────────────────────
with tab_feed:
    q = st.text_input("제목으로 찾기", key="admin_feed_q")
    items = db.feed_admin(q=q, limit=40)
    if not items:
        ui.empty("표시할 항목이 없습니다.")
    for it in items:
        with st.container(border=True):
            c1, c2, c3 = st.columns([6, 1, 1])
            state = " · ".join(x for x in ["고정" if it.get("is_pinned") else None,
                                           "숨김" if it.get("is_hidden") else None] if x)
            c1.markdown(f"[{it['title']}]({it['url']})  \n"
                        f"<span style='opacity:.65;font-size:.9em'>{it.get('kind')} · {it.get('venue') or ''} · "
                        f"{ui.fmt_date(it.get('published_at'))} {('· ' + state) if state else ''}</span>",
                        unsafe_allow_html=True)
            if c2.button("고정 해제" if it.get("is_pinned") else "고정", key=f"fpin_{it['id']}"):
                db.set_feed_item(it["id"], is_pinned=not it.get("is_pinned"))
                st.rerun()
            if c3.button("표시" if it.get("is_hidden") else "숨김", key=f"fhide_{it['id']}"):
                db.set_feed_item(it["id"], is_hidden=not it.get("is_hidden"))
                st.rerun()

# ── 수집 소스 ────────────────────────────────────────────────────
with tab_sources:
    st.caption("query는 방법별 문법을 따릅니다 — openalex/arxiv/gnews_rss: 검색식, rss: 피드 URL, "
               "youtube_rss: 채널 ID 또는 {\"channel_id\": \"...\", \"keywords\": [...]}. 저장하면 다음 수집부터 반영됩니다.")
    sources = db.sources()
    if not sources:
        ui.empty("소스가 없습니다.", "supabase/schema.sql의 초기 소스를 넣거나 SQL 편집기에서 행을 추가하세요.")
    else:
        cols = ["id", "active", "kind", "method", "name", "query", "lang", "weight"]
        df = pd.DataFrame(sources)[cols]
        edited = st.data_editor(
            df, hide_index=True, width="stretch", key="sources_editor",
            disabled=["id", "kind", "method"],
            column_config={
                "active": st.column_config.CheckboxColumn("사용"),
                "weight": st.column_config.NumberColumn("가중치", min_value=0.0, max_value=5.0, step=0.1),
                "query": st.column_config.TextColumn("query", width="large"),
            },
        )
        if st.button("소스 저장", type="primary"):
            changed = 0
            for orig, new in zip(df.to_dict("records"), edited.to_dict("records")):
                diff = {k: new[k] for k in ("active", "name", "query", "lang", "weight") if orig[k] != new[k]}
                if diff:
                    if "weight" in diff:
                        diff["weight"] = float(diff["weight"])
                    if "active" in diff:
                        diff["active"] = bool(diff["active"])
                    db.set_source(int(orig["id"]), **diff)
                    changed += 1
            st.success(f"{changed}개 소스를 저장했습니다." if changed else "바뀐 내용이 없습니다.")

    st.caption("수집은 GitHub → Actions → collect 워크플로 → Run workflow로 수동 실행할 수 있습니다.")

# ── harvest 반영 ─────────────────────────────────────────────────
with tab_harvest:
    st.caption("kwater-harvest 스킬이 만든 `_INDEX.md`를 올리면 OK 행이 피드에 추가됩니다. 이미 있는 URL은 건너뜁니다.")
    up = st.file_uploader("_INDEX.md", type=["md", "txt"], label_visibility="collapsed")
    if up is not None:
        text = up.getvalue().decode("utf-8", errors="replace")
        meta, rows, failed = parse_index(text)
        if not rows:
            st.warning("OK 상태의 행을 찾지 못했습니다. 인덱스 표 형식을 확인해 주세요.")
        else:
            st.write(f"{meta.get('institute') or '기관 미상'} {meta.get('institute_name') or ''} — "
                     f"OK {len(rows)}행, 실패/건너뜀 {failed}행")
            st.dataframe(pd.DataFrame(rows)[["title", "category", "date", "url"]], hide_index=True, width="stretch")
            if st.button("피드에 추가", type="primary"):
                n = db.insert_harvest(to_run(meta, rows, failed, text), to_feed_items(meta, rows))
                st.success(f"신규 {n}건을 추가했습니다.")
