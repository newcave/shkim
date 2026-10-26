# shkim — 김성훈 연구 페이지

GitHub 레포: **`newcave/shkim`** · 배포 주소(예정): `https://shkim.streamlit.app` (또는 Community Cloud가 배정하는 주소)

프로필·연구실적·미디어, Water Co-Scientist 자료 피드(매일 자동 수집), 게시판, 사이드바 유튜브.
설계 근거는 `research_page_design_v0.1.md`(설계서)를 따른다. 로컬 폴더명은 `newcave_water_coscientist`를 써도 되고, 레포명과 무관하다.

```
수집  collector/  ── GitHub Actions 매일 06:00 KST ──▶  Supabase (feed_items …)
표시  app.py + views/  ── Streamlit Community Cloud ──▶  방문자 (접근코드 링크)
```

## 1. 로컬에서 먼저 보기 (Supabase 없이, 5분)

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # DEMO_MODE = true 상태 그대로
streamlit run app.py
```

접근코드 `change-me`로 들어가면 샘플 데이터로 모든 페이지를 볼 수 있다.
프로필은 `content/profile.yaml`을 고치면 바로 반영된다. 사진은 `content/photo.jpg`로 두면 된다.

## 2. Supabase 준비

1. supabase.com에서 프로젝트 생성 (무료 플랜, 리전 Seoul 권장).
2. SQL Editor에 `supabase/schema.sql` 전체를 붙여 실행 → 테이블·RLS·초기 소스 생성.
3. Settings → API에서 Project URL과 `service_role` 키를 복사.
   `service_role` 키는 서버(앱·Actions)에서만 쓴다. 브라우저나 레포에 넣지 않는다.
4. `.streamlit/secrets.toml`의 `DEMO_MODE`를 `false`로 바꾸고 `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`를 채운 뒤 다시 실행.

무료 플랜은 일주일간 DB 활동이 없으면 일시정지된다. 수집기가 매일 DB에 쓰기 때문에 정상 운영 중에는 멈추지 않는다.

## 3. 배포 (Streamlit Community Cloud)

1. 이 폴더를 GitHub 레포로 올린다. 레포는 **비공개**로 두어도 된다.
2. share.streamlit.io → New app → 레포·브랜치·`app.py` 선택 → Advanced settings에 Python 3.12, Secrets에 `secrets.toml` 내용을 붙여넣기.
3. 배포 후 앱 Settings → Sharing에서 앱을 **공개(Public)** 로 전환한다. 접근코드가 게이트 역할을 한다.
   - 접근코드 링크: `https://<앱>.streamlit.app/?k=<APP_ACCESS_CODE>` — 이 링크를 공유하면 코드 입력 없이 들어간다.
   - 코드를 바꾸려면 Secrets의 `APP_ACCESS_CODE`만 고친다.
   - 이메일 초대 방식으로 바꾸려면 앱을 Private으로 두고 `APP_GATE_MODE = "invite"`.

## 4. 게시판 Google 인증 (선택이지만 관리 페이지에 필요)

1. Google Cloud Console → APIs & Services → Credentials → OAuth client ID (Web application).
2. 승인된 리디렉션 URI에 `https://<앱>.streamlit.app/oauth2callback` (로컬은 `http://localhost:8501/oauth2callback`).
3. `secrets.toml`의 `[auth]` 블록에 client_id / client_secret / redirect_uri를 채우고 `cookie_secret`은 긴 무작위 문자열로.
4. `ADMIN_EMAILS`에 본인 Google 계정을 넣으면 로그인 시 "관리" 페이지가 나타난다.

`[auth]` 블록이 없으면 인증 기능은 조용히 꺼지고, 게시판은 이름만으로 작성(승인제)된다.

## 5. 자동 수집 (GitHub Actions)

레포 Settings → Secrets and variables → Actions:

| 종류 | 이름 | 설명 |
|---|---|---|
| Secret | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | 필수 |
| Secret | `OPENALEX_EMAIL` | 선택. OpenAlex polite pool(더 빠른 응답) |
| Secret | `ANTHROPIC_API_KEY` | 선택. 신규 항목 한글 요약 |
| Variable | `SUMMARIZE` | `1`이면 요약 실행 (기본 0). 한 번에 40건까지 |

Actions 탭 → `collect` → Run workflow로 첫 수집을 돌린다. 이후 매일 06:00 KST 자동 실행.
수집 소스와 검색식은 앱의 관리 페이지(수집 소스 탭)에서 바꾼다. YouTube 소스는 채널 ID를 넣고 켠다
(채널 페이지 소스 보기에서 `"channelId"` 검색).

로컬 실행: `pip install -r requirements-collector.txt && SUPABASE_URL=… SUPABASE_SERVICE_KEY=… python -m collector.collect`

## 6. kwater-harvest 결과 반영

Claude에서 kwater-harvest 스킬을 실행해 받은 `_INDEX.md`를 관리 페이지 → harvest 반영 탭에 올리면 OK 행이 피드(kind: 논문/보고서/뉴스, 태그 `INST-XX`)로 들어간다.
CLI: `python -m scripts.import_harvest path/_INDEX.md`

## 7. 사이드바 유튜브

왼쪽 사이드바에 관련 영상이 뜬다. 설정은 `content/youtube.yaml` 한 파일:

- `channel_id` — 최신 영상을 자동으로 끌어올 채널 ID. 채널 페이지에서 소스 보기(Ctrl+U) → `channelId` 검색. 넣기 전까지는 자동 목록이 생략된다.
- `featured` — 항상 위에 고정할 추천 영상(URL + 제목). 채널 ID 없이도 이 영상들은 보인다.
- `channel_url` — '채널 보기' 링크(예: `https://www.youtube.com/@...`).

둘 다 비면 안내 문구만 뜨고 페이지는 멀쩡하다. 최신 영상은 1시간 캐시되고, 가져오기에 실패해도 사이드바는 깨지지 않는다.

## 8. 구조

```
app.py                 진입점: 스타일 → 접근 게이트 → st.navigation → 사이드바(YouTube)
views/                 home research media feed board admin
core/auth.py           게이트(code|invite), st.login 래퍼, 관리자 판정
core/db.py             Supabase 백엔드 + 데모 백엔드 (같은 함수 이름)
core/ui.py             스타일 한 블록, 히어로·경력 타임라인, 카드, 빈 상태
core/content.py        content/profile.yaml 로더
core/youtube_sidebar.py 사이드바 유튜브 (content/youtube.yaml)
collector/collect.py   소스 순회 → 정규화·중복 제거·태깅 → upsert → (요약)
collector/sources/     openalex arxiv gnews rss youtube
collector/config.py    태그 규칙 (키워드 → 태그)
scripts/import_harvest.py  _INDEX.md 파서 (관리 페이지와 공용)
supabase/schema.sql    테이블·인덱스·RLS·초기 소스
content/profile.yaml   홈 프로필·학력·경력 (이 파일만 고치면 반영)
content/youtube.yaml   사이드바 유튜브 설정
.github/workflows/collect.yml  매일 수집
```

## 9. 알아둘 것

- Community Cloud 무료 앱은 12시간 접속이 없으면 잠들고 다음 방문자가 깨운다(수십 초).
- Google News RSS는 비공식이라 형식이 바뀔 수 있다. 실패해도 다른 소스는 계속 수집된다. 링크는 구글 리다이렉트 주소다.
- 중복 판정은 URL/DOI 일치와 제목 유사도(0.92)로 한다. 다른 매체가 같은 제목을 쓰면 하나만 남는다.
- 요약 모델은 `SUMMARY_MODEL` 환경변수로 바꿀 수 있다. 모델 목록: https://docs.claude.com/en/docs/about-claude/models
