#!/usr/bin/env python3
"""supabase/schema.sql(앱 표 구조의 원본) → 연구소 서버용 setup.sql (shkim 전용 스키마·계정·권한을 앞뒤에 붙임).
schema.sql을 고치면 이것을 다시 실행해 setup.sql을 새로 만든다:  python supabase/institute/build_setup.py"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = (HERE.parent / "schema.sql").read_text(encoding="utf-8")
TABLES = re.findall(r"create table if not exists (\w+)", SCHEMA)

HEAD = """-- ============================================================================
-- shkim(김성훈 연구 페이지) 전용 공간 — 연구소 서버 Supabase(PostgreSQL)에 관리자(postgres)가 한 번 실행
-- 만들어지는 것: 스키마 shkim · 표 {n}개 · 역할 shkim_app(표 권한만, 로그인 불가) · shkim_authenticator(전용 PostgREST 접속용)
-- 건드리지 않는 것: 다른 스키마(archive·public·auth·storage …), 기존 역할·표·확장, 기존 Supabase 설정과 컨테이너
-- 비밀값 없음 (shkim_authenticator의 비밀번호는 mint_key.py가 만든 ~/.shkim/db_password.sql로 따로 넣음). 두 번 실행해도 됨.
-- 이 파일은 build_setup.py가 ../schema.sql에서 만든다 — 직접 고치지 말 것
-- ============================================================================
begin;

create schema if not exists shkim;

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'shkim_app') then
    create role shkim_app nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'shkim_authenticator') then
    create role shkim_authenticator noinherit nologin;
  end if;
end $$;

grant shkim_app to shkim_authenticator;
do $$ begin execute format('grant connect on database %I to shkim_authenticator', current_database()); end $$;
revoke all on schema shkim from public;
grant usage on schema shkim to shkim_app;
alter role shkim_app set statement_timeout = '15s';
alter role shkim_authenticator set statement_timeout = '15s';
alter role shkim_authenticator connection limit 10;

-- ── 앱 표 (../schema.sql 그대로, shkim 스키마 안에) ──────────────────────────
set local search_path to shkim, public, extensions;
"""

FOOT = """
-- ── 권한: shkim_app은 shkim 스키마의 표만 (다른 스키마는 권한 없음) ─────────
grant select, insert, update, delete on all tables in schema shkim to shkim_app;
grant usage, select on all sequences in schema shkim to shkim_app;
alter default privileges in schema shkim grant select, insert, update, delete on tables to shkim_app;
alter default privileges in schema shkim grant usage, select on sequences to shkim_app;

-- RLS는 켠 채로, shkim_app에게만 모든 행을 연다 (anon·authenticated 등 다른 역할은 권한 자체가 없음)
{policies}

commit;

-- 확인 (선택): shkim_app이 다른 스키마를 못 보는지
-- set role shkim_app; select count(*) from archive.paper_works;   -- → permission denied 가 정상
-- reset role;
"""


def main():
    body = SCHEMA
    # 원본 맨 위 안내(클라우드 Supabase·service_role 기준)는 여기와 맞지 않으므로 뺀다
    body = body[body.index("-- 수집 소스"):] if "-- 수집 소스" in body else body
    body = body.replace("-- RLS: 정책을 만들지 않으면 anon/authenticated는 아무것도 못 한다. service_role은 RLS를 우회한다.",
                        "-- RLS 켬 — 정책은 맨 아래(shkim_app만 열림)")
    body = re.sub(r"^\s*create extension if not exists pgcrypto;\s*$", "-- (pgcrypto: Supabase에 이미 있음 — gen_random_uuid()는 기본 함수)", body, flags=re.M)
    # 초기 소스는 비어 있을 때만 넣는다 (두 번 실행해도 중복 없게)
    body = re.sub(r"insert into sources \(([^)]*)\) values(.*?);",
                  lambda m: f"insert into sources ({m.group(1)})\nselect * from (values{m.group(2)}) v\nwhere not exists (select 1 from sources);",
                  body, flags=re.S)
    policies = "\n".join(
        f"drop policy if exists shkim_app_all on shkim.{t};\n"
        f"create policy shkim_app_all on shkim.{t} for all to shkim_app using (true) with check (true);" for t in TABLES)
    out = HEAD.format(n=len(TABLES)) + "\n" + body.strip() + "\n" + FOOT.format(policies=policies)
    (HERE / "setup.sql").write_text(out, encoding="utf-8")
    print(f"setup.sql — 표 {len(TABLES)}개: {', '.join(TABLES)}")


if __name__ == "__main__":
    main()
