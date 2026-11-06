#!/usr/bin/env python3
"""shkim 전용 PostgREST의 비밀값 세 가지를 서버에서 만든다 (파이썬 기본 모듈만 씀 — 설치 필요 없음).

  python3 mint_key.py              처음 한 번: ~/.shkim/ 에 아래 세 파일을 만든다 (이미 있으면 그대로 두고 열쇠만 다시 만듦)
  python3 mint_key.py --rotate     비밀을 새로 만든다 → 옛 열쇠는 모두 무효, db_password.sql 다시 실행·컨테이너 다시 시작

  ~/.shkim/db_password.sql   shkim_authenticator의 DB 비밀번호 한 줄 — setup.sql 다음에 한 번 실행
  ~/.shkim/pgrst.env         전용 PostgREST 설정(DB 접속 주소·JWT 비밀) — docker run --env-file 로만 씀
  ~/.shkim/service_key       앱·수집기에 줄 열쇠(JWT, role=shkim_app, 5년) — GitHub·Streamlit Secrets의 SUPABASE_SERVICE_KEY

세 파일 모두 주인만 읽기(600). 화면에는 비밀값을 찍지 않는다.
열쇠가 할 수 있는 일: shkim 스키마 표 6개 읽기·쓰기뿐 (다른 스키마·Supabase 본래 열쇠와 무관)."""
import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

ROLE = "shkim_app"
YEARS = 5


def b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def jwt(secret: str, claims: dict) -> str:
    head = b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = b64(json.dumps(claims, separators=(",", ":")).encode())
    sig = hmac.new(secret.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest()
    return f"{head}.{body}.{b64(sig)}"


def write600(p: Path, text: str):
    p.touch(mode=0o600, exist_ok=True)
    os.chmod(p, 0o600)
    p.write_text(text, encoding="utf-8")


def read_env(p: Path) -> dict:
    if not p.exists():
        return {}
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=str(Path.home() / ".shkim"), help="비밀 파일을 둘 폴더 (기본 ~/.shkim)")
    ap.add_argument("--db-host", default="127.0.0.1:5432",
                    help="PostgREST가 붙을 DB 주소 (기본 127.0.0.1:5432 = 서버에서 다른 앱이 쓰는 그 DB)")
    ap.add_argument("--db-user", default="shkim_authenticator",
                    help="접속 계정. Supavisor(풀러)를 거치면 'shkim_authenticator.<테넌트ID>' 꼴")
    ap.add_argument("--db-name", default="postgres")
    ap.add_argument("--port", type=int, default=3101, help="전용 PostgREST가 서버 안에서 열 포트 (기본 3101)")
    ap.add_argument("--rotate", action="store_true", help="DB 비밀번호·JWT 비밀을 새로 만든다")
    a = ap.parse_args()

    d = Path(a.dir).expanduser()
    d.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(d, 0o700)
    env_p = d / "pgrst.env"
    old = {} if a.rotate else read_env(env_p)

    jwt_secret = old.get("PGRST_JWT_SECRET") or secrets.token_urlsafe(48)
    uri = old.get("PGRST_DB_URI")
    made_pw = False
    if not uri:
        pw = secrets.token_urlsafe(32)
        uri = f"postgres://{a.db_user}:{pw}@{a.db_host}/{a.db_name}"
        write600(d / "db_password.sql",
                 f"alter role shkim_authenticator with login password '{pw}';\n")
        made_pw = True

    write600(env_p, "\n".join([
        "# shkim 전용 PostgREST — docker run --env-file 로만 씀. 커밋·공유 금지",
        f"PGRST_DB_URI={uri}",
        "PGRST_DB_SCHEMAS=shkim",
        f"PGRST_JWT_SECRET={jwt_secret}",
        "PGRST_SERVER_HOST=127.0.0.1",
        f"PGRST_SERVER_PORT={a.port}",
        "PGRST_DB_POOL=5",
        "PGRST_OPENAPI_MODE=disabled",
        "PGRST_LOG_LEVEL=error",
        "",
    ]))

    now = int(time.time())
    key = jwt(jwt_secret, {"role": ROLE, "iss": "ai4water-shkim", "iat": now, "exp": now + YEARS * 365 * 86400})
    write600(d / "service_key", key + "\n")

    print(f"폴더: {d}  (주인만 읽기)")
    if made_pw:
        print(f"  db_password.sql  새로 만듦 → setup.sql 다음에 한 번 실행 (psql -f 또는 SQL 편집기에 붙여넣기)")
    else:
        print(f"  db_password.sql  그대로 (이미 적용했다면 다시 실행할 필요 없음)")
    print(f"  pgrst.env        {'새 비밀' if a.rotate or not old else '같은 비밀'} · 포트 {a.port} · DB {a.db_host}")
    print(f"  service_key      새로 만듦 (role={ROLE}, {YEARS}년) → 요청자에게 안전한 경로로 전달 (메일·메신저 본문 말고 파일·사내 보안 경로)")
    if a.rotate:
        print("  ※ --rotate: db_password.sql 다시 실행 → docker restart shkim-rest → 새 service_key 전달")


if __name__ == "__main__":
    main()
