-- shkim 전용 공간 되돌리기 (관리자). 먼저: docker rm -f shkim-rest, nginx의 location /shkim-db/ 블록 삭제.
-- shkim 스키마와 그 안의 자료(수집 피드·게시판 글 등)가 모두 지워진다. 다른 스키마는 건드리지 않는다.
begin;
drop schema if exists shkim cascade;
do $$ begin
  if exists (select 1 from pg_roles where rolname = 'shkim_authenticator') then
    execute format('revoke connect on database %I from shkim_authenticator', current_database());
  end if;
end $$;
drop role if exists shkim_authenticator;
drop role if exists shkim_app;
commit;
