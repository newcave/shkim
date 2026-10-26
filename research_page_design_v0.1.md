# 김성훈 연구 페이지 — 설계서 v0.1

작성일 2026-08-30 (개정 2026-10-27) · 상태: 구현 착수 · 레포 `newcave/shkim`

개정 메모(10-27): 레포명 `newcave/shkim` 확정. 열람 게이트는 접근코드(B) 방식으로 시작. 저장소 Supabase. 게시판은 이름 입력 + Google 로그인 둘 다. 홈은 연구자 프로필형(사진·직책 히어로 + 경력 타임라인), 사이드바에 유튜브(고정 추천 + 채널 최신 자동) 추가.

---

## 1. 목적과 범위

**목적**
1. 프로필·연구실적·미디어 노출을 한 곳에 정리한다.
2. Water Co-Scientist 관련 자료(논문·뉴스·영상·기술보고서)를 매일 자동 수집해 열람한다.
3. 방문자가 피드백·질문을 남길 수 있는 게시판을 둔다.

**성격**: 개인 페이지이지만 회사 업무(연구 동향 공유·협업)용. 공개해도 무방한 정보만 게재한다.

**v1 비범위**: 댓글, 알림 메일, 검색엔진 노출, 다국어, 파일 업로드.

---

## 2. 확정 결정사항

| 항목 | 결정 | 비고 |
|---|---|---|
| 레포 | `newcave/shkim` | 배포 주소 shkim.streamlit.app |
| 호스팅 | Streamlit Community Cloud | 무료, GitHub 연동, 팀(Kwater-AILab) 전례 있음 |
| 공개 범위 | 링크 아는 사람만 (접근코드 B) | §4.1 |
| 저장소 | Supabase (Postgres) 무료 플랜 | 활성 프로젝트 2개, DB 500MB |
| 게시판 신원 | 이름만 입력 + Google 로그인 둘 다 | 로그인 글은 verified 배지, 즉시 노출 |
| 수집 주기 | GitHub Actions 매일 1회 | 06:00 KST, 수동 실행 가능 |
| 프로필 콘텐츠 | 레포 내 `content/profile.yaml` | 장문·버전관리에 유리. 나머지는 전부 DB |

---

## 3. 아키텍처 요약

```
[소스] 논문 API · 뉴스 RSS · YouTube RSS · kwater-harvest
   ↓
[수집] collector/collect.py  (GitHub Actions, 매일)
   ↓
[저장] Supabase Postgres  (sources · feed_items · publications · media · posts · harvest_runs)
   ↕
[표시] Streamlit 앱  (홈 · 연구 · 미디어 · 피드 · 게시판 · 관리)
   ↑
[방문자] 열람 · 게시판 작성
```

- 수집기와 앱은 같은 레포, 같은 DB를 쓴다. 앱은 읽기 + 게시판 쓰기 + 관리자 조작만 한다.
- 무료 플랜 상호작용: 수집기의 매일 DB 쓰기가 Supabase의 7일 비활성 일시정지를 자연스럽게 막는다. Streamlit은 12시간 무접속 시 슬립 → 첫 방문자가 수십 초 대기(허용).

---

## 4. 접근·인증 설계

### 4.1 열람 게이트 (택1, 설정값 `APP_GATE_MODE`로 전환)

**A. `invite` — Community Cloud 비공개 앱**
- 앱을 비공개로 두고 이메일 단위로 뷰어를 초대한다. 초대된 사람만 Google 로그인 또는 1회용 이메일 링크로 접속.
- 장점: 실제 접근 통제. 단점: 도메인 단위 허용 불가 → 인원 증가 시 초대 관리 부담, 회사 메일이 Google 계정이 아니면 매번 이메일 링크 로그인. 비공개 앱 슬롯 1개를 소모.

**B. `code` — 공개 앱 + 접근코드 (권장)**
- 레포는 비공개, 앱만 공개로 전환. 첫 화면에서 접근코드 입력(secrets 저장, 세션 동안 유지).
- 장점: 링크+코드만 공유하면 끝, 관리 0, 비공개 앱 슬롯을 남겨둠. 단점: 코드 유출 시 교체 필요(교체는 secrets 한 줄). 검색엔진에는 코드 화면만 노출.
- 게시 콘텐츠가 공개 가능 정보라는 전제에서 B로 시작하고, 민감도가 올라가면 A로 전환.

### 4.2 게시판 신원

| 경로 | 처리 |
|---|---|
| 이름만 입력 | 이름(필수)·소속(선택) → `is_verified=false`, `status=pending` → 관리자 승인 후 노출 |
| Google 인증 | "Google로 인증" 버튼 → `st.login()` (Streamlit 내장 OIDC) → 이메일 저장, `is_verified=true`, `status=approved` 즉시 노출, 배지 표시 |
| 관리자 | `ADMIN_EMAILS`에 있는 계정으로 Google 인증 시 관리 페이지 노출 |

- 스팸 방어: 미인증 글 승인제 + 세션당 작성 건수 제한 + 본문 링크 3개 이상이면 인증 여부와 무관하게 pending.
- 주의: Community Cloud 뷰어 로그인 정보(`st.user`)는 앱에서 안정적으로 읽히지 않는 사례가 있어 의존하지 않는다. 게시판 신원은 반드시 자체 `st.login`(Google OAuth 클라이언트)으로 처리한다.

---

## 5. 데이터 모델 (Supabase)

앱과 수집기는 모두 서버 측에서 `service_role` 키를 사용한다(브라우저에 노출되지 않음). 따라서 v1의 RLS는 "anon 전면 차단"으로 단순화하고, 규칙은 앱 코드에서 강제한다.

```sql
create extension if not exists pgcrypto;

-- 수집 소스 정의: 코드 수정 없이 키워드·소스를 조정
create table sources (
  id          serial primary key,
  kind        text not null check (kind in ('paper','news','video','report')),
  name        text not null,
  method      text not null,          -- openalex | arxiv | gnews_rss | rss | youtube_rss | harvest
  query       text,                   -- 검색식·키워드 또는 RSS URL
  lang        text default 'any',     -- ko | en | any
  weight      numeric default 1.0,    -- 점수 가중치
  active      boolean default true,
  created_at  timestamptz default now()
);

-- 수집 결과 (Water Co-Scientist 피드)
create table feed_items (
  id            uuid primary key default gen_random_uuid(),
  source_id     int references sources(id),
  kind          text not null,        -- paper | news | video | report
  title         text not null,
  url           text not null unique, -- 정규화된 URL (중복 차단 키)
  doi           text,
  authors       text,
  venue         text,                 -- 저널·매체·채널명
  published_at  date,
  lang          text,
  summary_ko    text,                 -- 선택: 자동 요약
  tags          text[] default '{}',
  score         numeric default 0,
  is_pinned     boolean default false,
  is_hidden     boolean default false,
  raw           jsonb,                -- 원본 메타데이터
  created_at    timestamptz default now()
);
create index on feed_items (published_at desc);
create index on feed_items using gin (tags);
create unique index feed_items_doi_uq on feed_items (doi) where doi is not null;

-- 본인 연구실적
create table publications (
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
create table media (
  id            serial primary key,
  kind          text not null check (kind in ('article','video')),
  title         text not null,
  url           text not null unique,
  outlet        text,                 -- 매체·채널
  published_at  date,
  note          text
);

-- 게시판
create table posts (
  id            uuid primary key default gen_random_uuid(),
  author_name   text not null,
  author_org    text,
  author_email  text,                 -- Google 인증 시에만
  is_verified   boolean default false,
  title         text not null,
  body          text not null,
  status        text default 'pending' check (status in ('pending','approved','hidden')),
  is_pinned     boolean default false,
  created_at    timestamptz default now()
);
create index on posts (status, created_at desc);

-- kwater-harvest 실행 이력
create table harvest_runs (
  id          serial primary key,
  institute   text,                   -- INST-01 ~ INST-07
  category    text,                   -- A_papers | B_technical | C_news
  run_at      timestamptz default now(),
  n_ok        int,
  n_failed    int,
  index_text  text                    -- _INDEX.md 원문
);
```

---

## 6. 수집 파이프라인

### 6.1 소스

| 종류 | 방법 | 키 필요 | 비고 |
|---|---|---|---|
| 논문 | OpenAlex API (검색 + 발행일 필터) | 없음 (polite pool용 이메일만) | 초록·DOI·OA 링크 제공 |
| 프리프린트 | arXiv API | 없음 | cs.AI, cs.CL, physics.ao-ph, eess.SP |
| 뉴스(국내외) | Google News RSS 키워드 검색 (ko/en) | 없음 | 비공식 피드라 형식 변경 가능 → 소스 단위 격리 |
| 뉴스(전문지) | 워터저널·물산업신문 등 RSS 또는 목록 페이지 | 없음 | RSS 없으면 HTML 파싱, 최소화 |
| 영상 | YouTube 채널 RSS (`channel_id`) | 없음 | 키워드 검색은 Data API(키 필요) → v2 |
| 심층 | kwater-harvest 스킬 (Claude) | — | 기관×범주 단위 실행 → §6.4 |

### 6.2 키워드 초안 (확정 필요)

- EN: `"Water Co-Scientist"`, `"AI co-scientist"`, `agentic AI` + (hydrology | water), `foundation model` + (hydrology | water), `LLM` + (water management | flood forecasting), `digital twin water`
- KO: 물관리 AI 에이전트, AI 코사이언티스트, 물 분야 거대언어모델, 디지털트윈 물관리, AI 정수장, 홍수예측 AI
- 소스별 키워드 조합은 `sources.query`에 저장 → 관리 페이지에서 on/off·수정.

### 6.3 처리 순서 (`collector/collect.py`)

1. `sources`에서 `active=true` 순회 → 후보 수집 (소스별 try/except, 하나가 실패해도 계속)
2. 정규화: URL에서 utm 제거·host 소문자, DOI 소문자 → `url`/`doi` unique로 중복 차단. 제목 유사도 0.9 초과도 중복 처리.
3. 태깅: `kind`, `lang`(문자 비율), `tags`(키워드 매칭), `score`(키워드 히트 수 × 소스 가중치)
4. 선택: 신규 항목만 Claude API로 2문장 한글 요약 → `summary_ko`
5. `feed_items` upsert → 실행 요약을 Actions 로그에 출력

- 스케줄: `.github/workflows/collect.yml` → `cron: "0 21 * * *"` (UTC 21:00 = KST 06:00) + `workflow_dispatch`
- 수집 규모 가정: 일 10~50건. 500MB DB 기준 수년치 여유.

### 6.4 kwater-harvest 연동

- 현재 문제: 스킬 산출물이 Claude 컨테이너 `~/kwater_harvest`에만 저장되어 세션 종료 시 사라진다. 컨테이너에서 Supabase로 직접 쓰기도 불가(네트워크 허용 목록 밖).
- v1: 스킬 실행 후 `_INDEX.md`를 파일로 내려받아 **관리 페이지의 "harvest 인덱스 업로드"**에 올리면 앱이 파싱해 `harvest_runs` 1행 + `feed_items`(kind=`report`) 행을 upsert. 추가 인프라 0.
- v2: Google Drive 폴더에 자동 저장 → Actions가 주 1회 동기화(서비스 계정 필요).

---

## 7. 페이지 설계 (`st.navigation`)

| 페이지 | 구성 |
|---|---|
| 홈 | 프로필 카드(사진·소속·한 줄 소개·링크), 최근 피드 5건, 최근 게시글 3건, 마지막 수집 시각 |
| 연구·발표 | `publications` 표. 연도/유형 필터, DOI 링크, `is_featured` 상단 고정 |
| 미디어 | 기사 카드(매체·날짜·링크), 유튜브 `st.video` 임베드 |
| 피드 | 검색창, kind/lang/tag 필터, 기간, 정렬(최신/점수). 카드: 제목·출처·날짜·요약·태그·원문 링크. 고정 항목 상단 |
| 게시판 | 승인 글 목록(verified 배지), 글쓰기 폼(이름/소속/제목/내용 + Google 인증 버튼), 운영 안내 |
| 관리 (소유자) | 대기 글 승인/숨김/고정, 피드 숨김/고정, 소스 on/off·키워드 수정, harvest 인덱스 업로드 |

**디자인 규칙 ("가장 깔끔한 방식")**
- 강조색 1개 (`.streamlit/config.toml` theme), 나머지는 무채색
- 사이드바는 내비게이션만, 페이지 상단에 제목 1줄 + 설명 1줄
- 카드는 `st.container(border=True)`, 열은 최대 3개(모바일에서 1열로 접힘)
- Pretendard 웹폰트 CSS 한 블록만 주입, 그 외 커스텀 CSS 금지
- 이모지·장식 아이콘 사용 안 함

---

## 8. 레포 구조

```
water-coscientist-page/
├── app.py                      # 진입점: 게이트 → st.navigation
├── views/
│   ├── home.py  research.py  media.py  feed.py  board.py  admin.py
├── core/
│   ├── db.py                   # supabase 클라이언트, 쿼리 함수
│   ├── auth.py                 # 게이트(invite|code), st.login 래퍼, 관리자 판정
│   └── ui.py                   # 카드·배지·폰트 주입
├── collector/
│   ├── collect.py              # 진입점
│   ├── sources/                # openalex.py arxiv.py gnews.py rss.py youtube.py
│   ├── normalize.py            # URL/DOI 정규화, 중복 판정
│   └── summarize.py            # 선택: 요약
├── scripts/import_harvest.py   # _INDEX.md 파서 (관리 페이지와 공유)
├── content/profile.yaml
├── supabase/schema.sql
├── .github/workflows/collect.yml
├── .streamlit/config.toml      # secrets.toml은 커밋 금지 (.gitignore)
├── requirements.txt
└── README.md
```

---

## 9. 배포·설정

**Streamlit secrets**
```
SUPABASE_URL, SUPABASE_SERVICE_KEY
APP_GATE_MODE = "code" | "invite"
APP_ACCESS_CODE            # code 모드일 때
ADMIN_EMAILS = ["..."]     # 관리자 Google 계정
[auth]                     # st.login (Google OIDC)
redirect_uri, cookie_secret, client_id, client_secret, server_metadata_url
```

**GitHub Actions secrets**: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `OPENALEX_EMAIL`, (선택) `ANTHROPIC_API_KEY`

**순서**
1. Supabase 프로젝트 생성(리전: Seoul) → `schema.sql` 실행 → `sources` 초기 행 입력
2. GitHub 레포 생성(비공개 권장) → 코드 푸시
3. Community Cloud에서 배포 → secrets 입력 → 게이트 방식에 맞게 앱 공개/비공개 설정
4. Google Cloud OAuth 클라이언트 생성 → 승인된 리디렉션 URI `https://<앱>.streamlit.app/oauth2callback`
5. Actions 수동 실행으로 첫 수집 → 피드 확인
6. `profile.yaml`, `publications`, `media` 입력

---

## 10. 로드맵

| 단계 | 산출물 | 예상 |
|---|---|---|
| 0 | 설계 확정(이 문서), 계정·준비물 | 이번 주 |
| 1 | 레포 골격, `schema.sql`, 게이트, 프로필 페이지 배포 | 1일 |
| 2 | 수집기 + Actions + 피드 페이지 | 2~3일 |
| 3 | 게시판 + Google 인증 + 관리 페이지 | 1~2일 |
| 4 | harvest 임포트, 요약 자동화, 키워드 튜닝 | 이후 반복 |

---

## 11. 준비물 체크리스트

- [ ] GitHub 계정 — 개인 레포로 할지 Kwater-AILab 조직 아래로 둘지 결정
- [ ] Supabase 계정·프로젝트 (무료)
- [ ] Google Cloud 프로젝트 + OAuth 클라이언트 ID (게시판 Google 인증용)
- [ ] 프로필 자료: 사진, 소속·직책, 약력, 외부 링크(GitHub·Scholar·LinkedIn), 논문·발표 목록, 기사·영상 링크
- [ ] 접근코드(B) 또는 초대 이메일 목록(A)
- [ ] 수집 키워드 확정 (§6.2)

---

## 12. 리스크·미결

- 공공기관 소속 개인 페이지 → 사내 겸직·보안·홍보 규정 확인 필요. 공개 가능 정보만 게재.
- Google News RSS는 비공식 → 형식 변경 시 해당 소스만 실패하도록 격리.
- 국내 전문지 RSS 부재 시 HTML 파싱은 깨지기 쉬움 → 최소한으로.
- Streamlit 슬립 후 첫 접속 지연 → 문제가 되면 외부 ping 또는 유료 호스팅 검토.
- 요약 자동화는 선택. 일 수십 건의 짧은 요약이라 비용은 작지만, 켜기 전에 한 달 추정치 확인.
- 동명이인이 많은 이름 → 프로필·실적은 본인 확인된 자료만 게재.
