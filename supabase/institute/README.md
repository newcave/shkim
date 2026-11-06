# 연구소 서버 Supabase에 shkim 자리 만들기

supabase.com 대신 **연구소 서버에 이미 돌고 있는 Supabase(PostgreSQL)** 에 이 앱의 표를 두는 방법이다.
기존 Supabase의 설정·컨테이너·열쇠(service_role)는 **하나도 바꾸지 않고**, 옆에 작은 문 하나만 새로 낸다.

```
앱(Streamlit Cloud)·수집기(GitHub Actions)
   │  https://<연구소 서버>/shkim-db/rest/v1/…   열쇠 = shkim 전용 (role shkim_app)
   ▼
nginx  location /shkim-db/rest/v1/  ──▶  shkim 전용 PostgREST (서버 안 127.0.0.1:3101, 컨테이너 shkim-rest)
                                              │  계정 shkim_authenticator → shkim_app 으로만 바뀜
                                              ▼
                                    기존 Supabase DB 안의 스키마 shkim (표 6개)  ← 여기만 읽고 씀
```

| 만드는 것 | 건드리지 않는 것 |
|---|---|
| 스키마 `shkim`, 표 6개(소스·피드·실적·미디어·게시판·harvest 기록) | 다른 스키마(public·auth·storage 및 다른 팀 자료) |
| 역할 `shkim_app`(로그인 불가, shkim 표 읽기·쓰기만) | 기존 역할·표·확장, Supabase 설정 파일 |
| 역할 `shkim_authenticator`(전용 PostgREST 접속용, 접속 10개·문장 15초 제한) | 기존 rest·kong·auth 컨테이너와 그 열쇠 |
| 컨테이너 `shkim-rest` 하나 (호스트 네트워크, 127.0.0.1:3101) | Supabase 도커 네트워크 (붙지 않음 → compose down/up에 영향 없음) |
| nginx `location /shkim-db/rest/v1/` 하나 | 다른 경로·기존 사이트·로그인 화면 |

## 관리자 할 일 (약 15분)

이 폴더(`supabase/institute/`)의 파일만 있으면 된다. 서버에서:

```bash
# 1) 비밀값 세 개 만들기 — ~/.shkim/ 에 주인만 읽기로 저장, 화면에 안 찍힘
#    DB 주소는 서버의 다른 앱이 쓰는 것과 같은 곳. 풀러(Supavisor)를 거치면 계정이 'shkim_authenticator.<테넌트ID>' 꼴
python3 mint_key.py --db-host 127.0.0.1:5432
#    (풀러라면)  python3 mint_key.py --db-host 127.0.0.1:5432 --db-user shkim_authenticator.<테넌트ID>

# 2) SQL 두 개를 관리자(postgres)로 실행 — Studio SQL 편집기에 붙여넣어도 됨
psql "<관리자 접속 주소>" -f setup.sql                # 스키마·역할·표·권한 (비밀값 없음, 두 번 실행해도 됨)
psql "<관리자 접속 주소>" -f ~/.shkim/db_password.sql   # shkim_authenticator 비밀번호 한 줄

# 3) 전용 PostgREST 켜기 (docker 권한) — 켜진 뒤 열쇠로 읽기까지 스스로 확인
bash run_rest.sh

# 4) nginx: nginx_shkim.conf 의 location 블록을 해당 server { listen 443 … } 안, location / 보다 위에 넣고
sudo nginx -t && sudo systemctl reload nginx

# 5) 바깥에서 확인 — 401이면 정상 (열쇠 없이 거절)
curl -s -o /dev/null -w '%{http_code}\n' https://<연구소 서버>/shkim-db/rest/v1/sources
```

6) `~/.shkim/service_key` 파일을 요청자에게 안전한 경로로 전달한다 (메일·메신저 본문에 붙이지 말 것).
   이 열쇠로 할 수 있는 일은 shkim 표 6개 읽기·쓰기뿐이고, 다른 역할로 바꿔 쓸 수 없다.

nginx를 고치지 않으려면 서버의 다른 길 안내(Caddy 등)에 `gate_shkim.caddy` 꼴로 같은 경로를 넣어도 된다.
DB 이름이 `postgres`가 아니면 `mint_key.py --db-name …`. 3101 포트를 이미 쓰면 `--port`로 바꾸고 nginx 쪽도 같이 바꾼다.

## 확인해 주실 것

1. **바깥 접속**: GitHub Actions(해외 IP)와 Streamlit Cloud에서 서버 443에 닿는가. 보안그룹이 기관 IP만 허용하면 알려 달라
   — 그때는 수집기를 서버 cron으로 돌리고(127.0.0.1:3101로 바로 씀) 앱도 서버 안으로 옮기는 안으로 바꾼다.
2. **서버 수집기 일정**: 이 수집기는 매일 06:00 KST에 한 번, 수십~수백 행을 쓴다. 서버 쪽 큰 작업과 겹치면 시간을 옮긴다.
3. **DB 접속 꼴**: 직접 접속인지, 풀러를 거치는지 (위 1번 `--db-user`).

## 서버의 다른 수집기와 겹치는 부분 (미리 정리)

| 겹칠 수 있는 것 | 정리 |
|---|---|
| 표 이름(`sources`, `posts` 등) | 스키마가 달라 섞이지 않는다. 같은 DB의 public에 같은 이름 표가 있어도 그대로 둠 (시험으로 확인) |
| 같은 논문이 두 곳에 | 이 피드(OpenAlex·arXiv·뉴스 신착, 소량)와 서버 쪽 논문 자료가 겹칠 수 있다. **지금은 따로 둔다** — 서버 표를 읽거나 고치지 않으며, 나중에 합칠 일이 있으면 DOI·OpenAlex ID로 잇는다 |
| OpenAlex 사용량 | 수집기는 GitHub에서 돌기 때문에 서버 IP의 무키 사용량과 겹치지 않는다. 서버 팀의 키를 쓰지 않는다. 나중에 서버 cron으로 옮기면 그때 조율 |
| DB 부하 | 하루 한 번, 접속 최대 10개(실제로는 PostgREST 5개), 문장당 15초 제한, 컨테이너 메모리 256MB |
| Supabase 본체 재시작 | DB가 다시 켜지는 동안만 shkim이 끊겼다가 저절로 다시 붙는다. shkim-rest는 Supabase 네트워크에 붙지 않아 compose 작업을 막지 않는다 |
| 열쇠 | Supabase 주인 열쇠(service_role)를 받지 않는다. shkim 열쇠로 service_role·postgres·다른 팀 계정으로 바꾸려 하면 거절된다 (시험으로 확인) |
| 개인정보 | 게시판 작성자 이메일(`posts.author_email`)이 서버에 저장된다 |

## 요청자 쪽 설정 (열쇠를 받은 뒤)

| 어디 | 이름 | 값 |
|---|---|---|
| GitHub → Settings → Secrets (Actions) | `SUPABASE_URL` | `https://<연구소 서버>/shkim-db` (`/rest/v1`은 붙이지 않음) |
| 〃 | `SUPABASE_SERVICE_KEY` | 받은 `service_key` 내용 |
| GitHub → Settings → Variables (Actions) | `SUPABASE_SCHEMA` | `shkim` |
| Streamlit Cloud → 앱 Settings → Secrets | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_SCHEMA = "shkim"`, `DEMO_MODE = false` | 위와 같음 |

넣은 뒤 Actions → `collect` → Run workflow. 첫 단계(DB 연결 정보 확인)가 실패하면 그 메시지가 원인을 알려 준다
(닿지 않음 = 방화벽, 401 = 열쇠, 404 = nginx 경로, 406 = SUPABASE_SCHEMA). 값이 아직 없으면 수집을 건너뛰고 경고만 남긴다.

## 파일

| 파일 | 무엇 |
|---|---|
| `setup.sql` | 스키마·역할·표·권한. `build_setup.py`가 `../schema.sql`(앱 표 구조의 원본)에서 만든다 — 표를 바꾸면 그쪽을 고치고 다시 만든다 |
| `mint_key.py` | 비밀값 세 개(DB 비밀번호·JWT 비밀·앱 열쇠). 파이썬 기본 모듈만. `--rotate`로 모두 바꾸기 |
| `run_rest.sh` | 전용 PostgREST 컨테이너 켜기 + 스스로 확인 |
| `nginx_shkim.conf` / `gate_shkim.caddy` | 길 하나 (nginx 또는 Caddy 중 하나) |
| `rollback.sql` | 되돌리기 — `docker rm -f shkim-rest`, nginx 블록 삭제 뒤 실행. shkim 스키마와 역할만 지운다 |

## 시험 (2026-11-06, 로컬 PostgreSQL 16 + PostgREST 12.2.3 + supabase-py 2.34)

- 관리자를 슈퍼유저가 아닌 계정(CREATEROLE)으로 흉내 내 `setup.sql` 두 번 실행 → 오류 없음, 초기 소스 중복 없음, public의 같은 이름 표 그대로.
- 열쇠 없이 401 · 다른 비밀로 서명 401 · 같은 비밀이라도 role을 service_role·postgres·다른 팀 계정으로 바꾸면 403 · 다른 스키마 지정 406.
- shkim_app으로 다른 스키마 읽기·public 표 읽기·표 만들기 모두 거절, shkim 표 읽기·쓰기만 됨.
- nginx와 같은 경로 떼기(`/shkim-db/rest/v1/` → `/`)를 거쳐 수집기(`collector/store.py`) 함수 전부와 앱 백엔드(`core/db.py`) 함수 전부,
  앱 화면 5개(AppTest, 예외 0) 확인. 워크플로 첫 단계의 경우별 메시지(값 없음·정상·401·404·406·닿지 않음) 확인.
- `rollback.sql` 뒤 다른 스키마 자료 그대로, `setup.sql` 다시 실행해 복구됨.
