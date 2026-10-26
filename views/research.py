import pandas as pd
import streamlit as st

from core import db, ui
from core.db import PUB_TYPE_LABEL

ui.page_header("연구·발표", "논문, 학술발표, 보고서, 특허를 연도별로 정리합니다.")

pubs = db.publications()
if not pubs:
    ui.empty("등록된 실적이 없습니다.", "Supabase의 publications 테이블에 행을 추가하면 표시됩니다.")
    st.stop()

featured = [p for p in pubs if p.get("is_featured")]
if featured:
    st.markdown("#### 대표 실적")
    cols = st.columns(min(3, len(featured)))
    for i, p in enumerate(featured):
        with cols[i % len(cols)], st.container(border=True):
            link = p.get("url") or (f"https://doi.org/{p['doi']}" if p.get("doi") else None)
            st.markdown(f"**[{p['title']}]({link})**" if link else f"**{p['title']}**")
            st.caption(" · ".join(x for x in [str(p.get("year")), PUB_TYPE_LABEL.get(p.get("type"), p.get("type")),
                                              p.get("venue")] if x))
            st.caption(p.get("authors") or "")

st.markdown("#### 전체 목록")
years = sorted({p["year"] for p in pubs if p.get("year")}, reverse=True)
types = [t for t in PUB_TYPE_LABEL if any(p.get("type") == t for p in pubs)]
f1, f2 = st.columns([2, 3])
with f1:
    sel_years = st.multiselect("연도", years, placeholder="전체 연도")
with f2:
    sel_types = st.pills("유형", types, selection_mode="multi", format_func=lambda t: PUB_TYPE_LABEL[t])

rows = [p for p in pubs
        if (not sel_years or p.get("year") in sel_years) and (not sel_types or p.get("type") in sel_types)]
if not rows:
    ui.empty("조건에 맞는 실적이 없습니다.", "필터를 지우면 전체가 보입니다.")
    st.stop()

df = pd.DataFrame([{
    "연도": p.get("year"),
    "유형": PUB_TYPE_LABEL.get(p.get("type"), p.get("type")),
    "제목": p.get("title"),
    "저자": p.get("authors"),
    "게재처": p.get("venue"),
    "링크": p.get("url") or (f"https://doi.org/{p['doi']}" if p.get("doi") else None),
    "PDF": p.get("pdf_url"),
} for p in rows])
st.dataframe(
    df,
    hide_index=True,
    width="stretch",
    column_config={
        "연도": st.column_config.NumberColumn(format="%d", width="small"),
        "유형": st.column_config.TextColumn(width="small"),
        "제목": st.column_config.TextColumn(width="large"),
        "링크": st.column_config.LinkColumn(display_text="열기", width="small"),
        "PDF": st.column_config.LinkColumn(display_text="PDF", width="small"),
    },
)
st.caption(f"{len(rows)}건")
