"""소스 모듈 공통: HTTP GET(재시도 1회, 403/429는 즉시 포기), 날짜 변환."""
from __future__ import annotations

import datetime as dt
import time

import requests

UA = "water-coscientist-collector/0.1 (personal research feed)"


def get(url: str, params: dict | None = None, timeout: int = 30, retries: int = 1) -> requests.Response:
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": UA})
            r.raise_for_status()
            return r
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code in (403, 429):
                raise
            last = e
        except requests.RequestException as e:
            last = e
        if attempt < retries:
            time.sleep(5)
    assert last is not None
    raise last


def date_from_struct(struct) -> str | None:
    if not struct:
        return None
    try:
        return dt.date(struct.tm_year, struct.tm_mon, struct.tm_mday).isoformat()
    except (TypeError, ValueError, AttributeError):
        return None
