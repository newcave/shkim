"""신규 항목에 두 문장 한글 요약을 붙인다(선택).

켜는 조건: 환경변수 SUMMARIZE=1 과 ANTHROPIC_API_KEY. 한 번 실행에 SUMMARY_MAX(기본 40)건까지.
모델은 SUMMARY_MODEL로 바꿀 수 있다. 현재 모델 목록: https://docs.claude.com/en/docs/about-claude/models
"""
from __future__ import annotations

import os

DEFAULT_MODEL = "claude-haiku-4-5-20251001"

PROMPT = (
    "다음 자료를 한국어 두 문장으로 요약해 주세요. 첫 문장은 핵심 내용, 둘째 문장은 물관리·AI 연구 관점에서의 의미입니다. "
    "군더더기 없이 문장만 출력하세요.\n\n제목: {title}\n출처: {venue}\n종류: {kind}\n본문:\n{text}"
)


def enabled() -> bool:
    return os.environ.get("SUMMARIZE", "0") == "1" and bool(os.environ.get("ANTHROPIC_API_KEY"))


def summarize(title: str, venue: str | None, kind: str, text: str) -> str | None:
    from anthropic import Anthropic

    client = Anthropic()
    msg = client.messages.create(
        model=os.environ.get("SUMMARY_MODEL", DEFAULT_MODEL),
        max_tokens=220,
        messages=[{"role": "user", "content": PROMPT.format(
            title=title, venue=venue or "-", kind=kind, text=(text or "")[:3000] or "(본문 없음, 제목만으로 요약)")}],
    )
    out = "".join(getattr(b, "text", "") for b in msg.content).strip()
    return out or None


def summarize_new(store, new_rows: list[dict], texts: dict[str, str]) -> int:
    """store.set_summary로 저장. 돌려주는 값은 요약한 건수."""
    if not enabled():
        return 0
    limit = int(os.environ.get("SUMMARY_MAX", "40"))
    done = 0
    for row in new_rows[:limit]:
        try:
            summary = summarize(row["title"], row.get("venue"), row["kind"], texts.get(row["url"], ""))
        except Exception as e:  # 요약 실패는 수집을 막지 않는다
            print(f"  요약 실패: {row['title'][:50]} — {e}")
            continue
        if summary:
            store.set_summary(row["id"], summary)
            done += 1
    return done
