-- Supabase SQL 편집기에 통째로 붙여넣어 실행한다.
-- 앱과 수집기는 서버 측에서 service_role 키로 접근하므로 RLS는 anon/authenticated 전면 차단으로 둔다.

create extension if not exists pgcrypto;

-- 수집 소스: 코드 수정 없이 관리 페이지에서 켜고 끄고 검색식을 바꾼다
create table if not exists sources (
  id          serial primary key,
  kind        text not null check (kind in ('paper','news','video','report')),
  name        text not null,
  method      text not null check (method in ('openalex','arxiv','gnews_rss','rss','youtube_rss','harvest')),
  query       text,
  lang        text default 'any',
  weight      numeric default 1.0,
  active      boolean default true,
  created_at  timestamptz default now()
);

-- 수집 결과 (Co-Scientist 피드)
create table if not exists feed_items (
  id            uuid primary key default gen_random_uuid(),
  source_id     int references sources(id) on delete set null,
  kind          text not null check (kind in ('paper','news','video','report')),
  title         text not null,
  url           text not null unique,
  doi           text,
  authors       text,
  venue         text,
  published_at  date,
  lang          text,
  summary_ko    text,
  tags          text[] default '{}',
  score         numeric default 0,
  is_pinned     boolean default false,
  is_hidden     boolean default false,
  raw           jsonb,
  created_at    timestamptz default now()
);
create index if not exists feed_items_published_idx on feed_items (published_at desc);
create index if not exists feed_items_created_idx on feed_items (created_at desc);
create index if not exists feed_items_tags_idx on feed_items using gin (tags);
create unique index if not exists feed_items_doi_uq on feed_items (doi) where doi is not null;

-- 본인 연구실적
create table if not exists publications (
  id           serial primary key,
  year         int not null,
  type         text not null check (type in ('journal','conference','report','talk','patent')),
  title        text not null,
  authors      text not null,
  venue        text,
  doi          text,
  url          text,
  pdf_url      text,
  is_featured  boolean default false,
  note         text
);

-- 기사·영상
create table if not exists media (
  id            serial primary key,
  kind          text not null check (kind in ('article','video')),
  title         text not null,
  url           text not null unique,
  outlet        text,
  published_at  date,
  note          text
);

-- 게시판
create table if not exists posts (
  id            uuid primary key default gen_random_uuid(),
  author_name   text not null,
  author_org    text,
  author_email  text,
  is_verified   boolean default false,
  title         text not null,
  body          text not null,
  status        text default 'pending' check (status in ('pending','approved','hidden')),
  is_pinned     boolean default false,
  created_at    timestamptz default now()
);
create index if not exists posts_status_idx on posts (status, created_at desc);

-- kwater-harvest 실행 이력
create table if not exists harvest_runs (
  id          serial primary key,
  institute   text,
  category    text,
  run_at      timestamptz default now(),
  n_ok        int,
  n_failed    int,
  index_text  text
);

-- RLS: 정책을 만들지 않으면 anon/authenticated는 아무것도 못 한다. service_role은 RLS를 우회한다.
alter table sources       enable row level security;
alter table feed_items    enable row level security;
alter table publications  enable row level security;
alter table media         enable row level security;
alter table posts         enable row level security;
alter table harvest_runs  enable row level security;

-- 초기 수집 소스 (관리 페이지에서 수정 가능)
insert into sources (kind, name, method, query, lang, weight, active) values
  ('paper', 'OpenAlex — co-scientist / agentic AI × water', 'openalex',
   '("co-scientist" OR "agentic AI" OR "foundation model" OR "large language model") AND (water OR hydrology OR flood OR "water treatment")',
   'en', 1.5, true),
  ('paper', 'arXiv — LLM/agent × water', 'arxiv',
   '(abs:"co-scientist" OR abs:agentic OR abs:"foundation model" OR abs:"language model") AND (abs:water OR abs:hydrology OR abs:flood)',
   'en', 1.2, true),
  ('news', '구글뉴스 — 물관리 AI (한국어)', 'gnews_rss',
   '물관리 AI OR "AI 정수장" OR "디지털트윈 물관리" OR "홍수예측 AI" OR "수자원공사 AI"',
   'ko', 1.0, true),
  ('news', 'Google News — AI water management (EN)', 'gnews_rss',
   '("water management" OR hydrology OR "flood forecasting") AND (agent OR "co-scientist" OR "foundation model" OR LLM)',
   'en', 0.8, true),
  ('video', 'YouTube — 채널 ID를 넣고 켜세요', 'youtube_rss',
   '{"channel_id": "UCxxxxxxxxxxxxxxxxxxxxxx", "keywords": ["AI", "디지털", "데이터", "물관리"]}',
   'ko', 0.8, false);

-- 본인 확인 후 주석을 풀어 쓰는 예시 (공개 검색에서 확인된 후보)
-- insert into publications (year, type, title, authors, venue, url, is_featured) values
--   (2021, 'conference', '디지털 트윈 기술 기반 스마트 물관리 플랫폼 개발', '김성훈 외', '대한토목학회 학술대회',
--    'https://www.dbpia.co.kr/journal/articleDetail?nodeId=NODE11223735', true),
--   (2022, 'talk', 'K-water''s Big Challenges for Digital Transformation in Smart Water Management', '김성훈',
--    'UKC 2022', 'https://github.com/Kwater-AILab', false);
