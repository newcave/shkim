"""URL·DOI 정규화, 언어 판정, 제목 중복 판정, 태그·점수."""
from __future__ import annotations

import html
import re
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from collector.config import KO_RATIO, NEAR_DUP, TAG_RULES

_TRACKING_PREFIXES = ("utm_",)
_TRACKING_KEYS = {"fbclid", "gclid", "igshid", "mc_cid", "mc_eid", "ref", "ref_src", "spm"}
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        return None
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=False)
             if not k.lower().startswith(_TRACKING_PREFIXES) and k.lower() not in _TRACKING_KEYS]
    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    d = doi.strip().lower()
    d = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", d)
    return d or None


def clean_text(text: str | None, limit: int = 4000) -> str:
    if not text:
        return ""
    t = html.unescape(_TAG_RE.sub(" ", text))
    return _WS_RE.sub(" ", t).strip()[:limit]


def detect_lang(text: str) -> str:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "other"
    ko = sum(1 for c in letters if "가" <= c <= "힣")
    if ko / len(letters) >= KO_RATIO:
        return "ko"
    latin = sum(1 for c in letters if c.isascii())
    return "en" if latin / len(letters) >= 0.6 else "other"


def title_key(title: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", (title or "").lower())


def is_near_duplicate(title: str, known_keys: list[str]) -> bool:
    key = title_key(title)
    if not key:
        return False
    for k in known_keys:
        if k == key:
            return True
        if abs(len(k) - len(key)) <= 12 and SequenceMatcher(None, key, k).ratio() >= NEAR_DUP:
            return True
    return False


def tag_and_score(text: str, weight: float = 1.0) -> tuple[list[str], float]:
    low = (text or "").lower()
    tags, hits = [], 0
    for tag, keywords in TAG_RULES.items():
        n = sum(1 for kw in keywords if kw in low)
        if n:
            tags.append(tag)
            hits += n
    return tags, round(hits * float(weight), 2)
