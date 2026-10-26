"""진입점. `streamlit run app.py`"""
import streamlit as st

from core import auth, db, ui, youtube_sidebar

st.set_page_config(
    page_title="김성훈 · Water Co-Scientist",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"Get help": None, "Report a bug": None},
)
ui.inject_style()

if not auth.gate():
    st.stop()

pages = [
    st.Page("views/home.py", title="홈", default=True),
    st.Page("views/research.py", title="연구·발표"),
    st.Page("views/media.py", title="미디어"),
    st.Page("views/feed.py", title="Co-Scientist 피드"),
    st.Page("views/board.py", title="게시판"),
]
if auth.is_admin():
    pages.append(st.Page("views/admin.py", title="관리"))

nav = st.navigation(pages, position="sidebar")

with st.sidebar:
    st.markdown("**김성훈**  \nWater Co-Scientist")
    if db.is_demo():
        st.caption("데모 모드 — 샘플 데이터를 보고 있습니다.")

youtube_sidebar.render()
auth.render_sidebar_account()

nav.run()
