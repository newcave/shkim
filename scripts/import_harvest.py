"""kwater-harvest 스킬이 만든 `_INDEX.md`를 피드에 넣는다.

관리 페이지의 업로드와 CLI가 같은 파서를 쓴다.

CLI:
    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python -m scripts.import_harvest path/to/_INDEX.md
"""
from __future__ import annotations

import datetime as dt
import re
import sys

HEADER_RE = re.compile(r"^#\s*(INST-\d{2})\s+(\S+)\s+자료 인덱스", re.M)
ROW_RE = re.compile(
    r"^\|\s*(\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$", re.M
)
CATEGORY_KIND = {"A_papers": "paper", "B_technical": "report", "C_news": "news"}
INSTITUTE_NAME = {
    "INST-01": "경영연구소", "INST-02": "수자원환경연구소", "INST-03": "상하수도연구소",
    "INST-04": "물인프라안전연구소", "INST-05": "물에너지연구소", "INST-06": "수자원위성연구소",
    "INST-07": "AI연구소",
}


def parse_index(text: str) -> tuple[dict, list[dict], int]:
    """(메타, OK 행 목록, 실패/건너뜀 행 수)를 돌려준다."""
    m = HEADER_RE.search(text)
    institute = m.group(1) if m else None
    name = m.group(2) if m else INSTITUTE_NAME.get(institute or "", "")
    rows, failed = [], 0
    for mm in ROW_RE.finditer(text):
        _, fname, title, category, date, url, status = (g.strip() for g in mm.groups())
        if fname.lower() in ("file name", "---") or title in ("Title", "-----"):
            continue
        if not status.upper().startswith("OK") or not url.startswith("http"):
            failed += 1
            continue
        rows.append({"file": fname, "title": title, "category": category, "date": date, "url": url})
    return {"institute": institute, "institute_name": name}, rows, failed


def _date(value: str) -> str | None:
    value = (value or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value
    if re.fullmatch(r"\d{4}-\d{2}", value):
        return f"{value}-01"
    if re.fullmatch(r"\d{4}", value):
        return f"{value}-01-01"
    return None


def to_feed_items(meta: dict, rows: list[dict]) -> list[dict]:
    institute = meta.get("institute") or "INST-00"
    venue = f"K-water {meta.get('institute_name') or ''}".strip()
    items = []
    for r in rows:
        title = r["title"]
        text = f"{title} {r['file']}"
        items.append({
            "kind": CATEGORY_KIND.get(r["category"], "report"),
            "title": title,
            "url": r["url"],
            "doi": None,
            "authors": None,
            "venue": venue,
            "published_at": _date(r["date"]),
            "lang": "ko" if re.search(r"[가-힣]", text) else "en",
            "tags": [institute, r["category"], "kwater-harvest"],
            "score": 1,
            "raw": {"file": r["file"], "category": r["category"]},
        })
    return items


def to_run(meta: dict, rows: list[dict], failed: int, index_text: str) -> dict:
    categories = sorted({r["category"] for r in rows})
    return {
        "institute": meta.get("institute"),
        "category": ",".join(categories) if categories else None,
        "run_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "n_ok": len(rows),
        "n_failed": failed,
        "index_text": index_text,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    text = open(argv[1], encoding="utf-8").read()
    meta, rows, failed = parse_index(text)
    if not rows:
        print("OK 상태의 행이 없습니다.")
        return 1
    from collector.store import Store

    store = Store.from_env()
    inserted = store.insert_harvest(to_run(meta, rows, failed, text), to_feed_items(meta, rows))
    print(f"{meta['institute']}: OK {len(rows)}행 중 신규 {inserted}건 추가, 실패/건너뜀 {failed}행")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
