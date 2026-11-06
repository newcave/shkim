#!/usr/bin/env bash
# shkim 전용 PostgREST 켜기 (서버 관리자, docker 권한 필요) — mint_key.py를 먼저 실행해 ~/.shkim/pgrst.env가 있어야 한다.
#   bash run_rest.sh            켜기 (이미 있으면 지우고 새로 — 설정을 바꾼 뒤에도 이것)
#   docker logs shkim-rest      기록 보기 /  docker rm -f shkim-rest   끄기·없애기
# 호스트 네트워크로 서버 안 127.0.0.1:3101에서만 연다 → Supabase 도커 네트워크에 붙지 않으므로 docker compose down/up에 영향 없음.
set -euo pipefail
ENV_FILE="${SHKIM_ENV:-$HOME/.shkim/pgrst.env}"
# 기존 Supabase의 rest 컨테이너와 같은 이미지를 써도 된다 (docker ps에서 postgrest/postgrest:… 확인 후 IMAGE=… bash run_rest.sh)
IMAGE="${IMAGE:-postgrest/postgrest:v12.2.3}"

[ -r "$ENV_FILE" ] || { echo "설정 파일이 없습니다: $ENV_FILE  (python3 mint_key.py 먼저)"; exit 1; }
PORT=$(grep -E '^PGRST_SERVER_PORT=' "$ENV_FILE" | cut -d= -f2)
if docker ps -a --format '{{.Names}}' | grep -qx shkim-rest; then
  docker rm -f shkim-rest >/dev/null
elif ss -ltn 2>/dev/null | grep -q ":${PORT} "; then
  echo "포트 ${PORT}을 이미 다른 프로그램이 씁니다. mint_key.py --port 다른번호 로 다시 만든 뒤 nginx 설정의 포트도 같이 바꾸세요."; exit 1
fi
docker run -d --name shkim-rest --restart unless-stopped --network host \
  --memory 256m --cpus 0.5 \
  --env-file "$ENV_FILE" "$IMAGE" >/dev/null
KEY_FILE="$(dirname "$ENV_FILE")/service_key"
code=000
for _ in 1 2 3 4 5 6; do
  sleep 2
  code=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $(cat "$KEY_FILE")" "http://127.0.0.1:${PORT}/sources?select=id&limit=1" || true)
  [ "$code" = 200 ] && break
done
if [ "$code" = 200 ]; then
  echo "shkim-rest 켜짐 — 127.0.0.1:${PORT} (열쇠로 shkim.sources 읽기 확인)"
  echo "열쇠 없이 묻기 → $(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${PORT}/sources") (401이 정상)"
else
  echo "확인 실패 (응답 ${code}). 기록: docker logs --tail 20 shkim-rest"
  echo "  흔한 원인: db_password.sql 미실행 · DB 주소/계정 꼴(풀러면 shkim_authenticator.<테넌트>) · setup.sql 미실행"
  exit 1
fi
