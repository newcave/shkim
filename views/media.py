import streamlit as st

from core import db, ui

ui.page_header("미디어", "기사와 영상으로 본 활동.")

items = db.media()
articles = [m for m in items if m.get("kind") == "article"]
videos = [m for m in items if m.get("kind") == "video"]

if not items:
    ui.empty("등록된 기사나 영상이 없습니다.", "Supabase의 media 테이블에 행을 추가하면 표시됩니다.")
    st.stop()

if videos:
    st.markdown("#### 영상")
    cols = st.columns(2, gap="large")
    for i, v in enumerate(videos):
        with cols[i % 2], st.container(border=True):
            st.video(v["url"])
            st.markdown(f"**{v['title']}**")
            st.caption(" · ".join(x for x in [v.get("outlet"), ui.fmt_date(v.get("published_at"))] if x))
            if v.get("note"):
                st.write(v["note"])

if articles:
    st.markdown("#### 기사")
    for a in articles:
        with st.container(border=True):
            st.markdown(f"**[{a['title']}]({a['url']})**")
            st.caption(" · ".join(x for x in [a.get("outlet"), ui.fmt_date(a.get("published_at"))] if x))
            if a.get("note"):
                st.write(a["note"])
