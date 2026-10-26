import re

import streamlit as st

from core import auth, db, ui

MAX_PER_SESSION = 3
LINK_RE = re.compile(r"https?://")

ui.page_header("게시판", "질문, 제안, 피드백을 남겨 주세요. 인증 없이 올린 글은 확인 후 게시됩니다.")

tab_list, tab_write = st.tabs(["글 목록", "글쓰기"])

with tab_list:
    posts = db.posts()
    if posts:
        for p in posts:
            ui.post_card(p)
    else:
        ui.empty("아직 게시된 글이 없습니다.", "글쓰기 탭에서 첫 글을 남겨 주세요.")

with tab_write:
    user = auth.current_user()
    if user:
        st.caption(f"{user['name']} ({user['email']}) 계정으로 작성합니다. 글은 바로 게시되고 인증 표시가 붙습니다.")
    elif auth.auth_configured():
        col_a, col_b = st.columns([3, 1])
        col_a.caption("Google 계정으로 확인하면 글이 바로 게시되고 인증 표시가 붙습니다. 확인 없이도 올릴 수 있습니다.")
        if col_b.button("Google로 확인", width="stretch"):
            st.login()
    else:
        st.caption("이름을 적고 올리면 관리자가 확인한 뒤 게시됩니다.")

    with st.form("post_form", border=True):
        name = st.text_input("이름", value=user["name"] if user else "", max_chars=40)
        org = st.text_input("소속 (선택)", max_chars=60)
        title = st.text_input("제목", max_chars=120)
        body = st.text_area("내용", height=180, max_chars=4000)
        submitted = st.form_submit_button("올리기", type="primary")

    if submitted:
        problems = []
        if not name.strip():
            problems.append("이름을 적어 주세요.")
        if not title.strip():
            problems.append("제목을 적어 주세요.")
        if len(body.strip()) < 5:
            problems.append("내용을 조금 더 적어 주세요.")
        if st.session_state.get("posts_made", 0) >= MAX_PER_SESSION:
            problems.append(f"한 번 접속에 {MAX_PER_SESSION}건까지 올릴 수 있습니다.")
        if problems:
            for msg in problems:
                st.error(msg)
        else:
            verified = bool(user)
            many_links = len(LINK_RE.findall(body)) >= 3
            status = "approved" if verified and not many_links else "pending"
            db.create_post({
                "author_name": name.strip(),
                "author_org": org.strip() or None,
                "author_email": user["email"] if user else None,
                "is_verified": verified,
                "title": title.strip(),
                "body": body.strip(),
                "status": status,
            })
            st.session_state["posts_made"] = st.session_state.get("posts_made", 0) + 1
            if status == "approved":
                st.success("올렸습니다. 글 목록에서 확인할 수 있습니다.")
            else:
                st.success("올렸습니다. 관리자가 확인한 뒤 게시됩니다.")
