#!/usr/bin/env bash
set -Eeuo pipefail
image="${1:?image required}"
network="aa-smoke-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}"
pg="aa-smoke-pg"
redis="aa-smoke-redis"
server="aa-smoke-server"
cleanup() {
  docker rm -f "$server" "$pg" "$redis" >/dev/null 2>&1 || true
  docker network rm "$network" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker network create --internal "$network" >/dev/null
docker run -d --name "$pg" --network "$network" \
  -e POSTGRES_USER=agents_anywhere -e POSTGRES_DB=agents_anywhere \
  -e POSTGRES_PASSWORD=ci-only-not-a-real-credential postgres:17-alpine >/dev/null
docker run -d --name "$redis" --network "$network" redis:8-alpine \
  redis-server --save '' --appendonly yes --maxmemory 256mb --maxmemory-policy noeviction >/dev/null
ready=0
for ((attempt=0; attempt<60; attempt++)); do
  if docker exec "$pg" pg_isready -U agents_anywhere -d agents_anywhere >/dev/null 2>&1 \
    && docker exec "$redis" redis-cli ping | grep -q PONG; then
    ready=1
    break
  fi
  sleep 2
done
[[ "$ready" == 1 ]] || { echo 'Database or Redis failed to start'; exit 1; }
database_url="postgresql+asyncpg://agents_anywhere:ci-only-not-a-real-credential@${pg}:5432/agents_anywhere"
docker run --rm --network "$network" -e "AGENT_SERVER_DB_URL=$database_url" "$image" \
  /opt/venv/bin/python -m agent_server.infra.db.migrations upgrade
secret="$(openssl rand -hex 32)"
docker run -d --name "$server" --network "$network" \
  -e "AGENT_SERVER_DB_URL=$database_url" \
  -e "AGENT_SERVER_REDIS_URL=redis://${redis}:6379/0" \
  -e "AGENT_SERVER_SECRET=$secret" \
  -e AGENT_SERVER_HOST=0.0.0.0 -e AGENT_SERVER_PORT=8000 \
  -e AGENT_SERVER_WORKERS=1 -e AGENT_SERVER_FILES_LOCAL_ROOT=/data/agent-server.files \
  "$image" >/dev/null
for ((attempt=0; attempt<60; attempt++)); do
  if docker exec "$server" /opt/venv/bin/python -c \
    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v2/health/ready', timeout=3).close(); urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3).close()" >/dev/null 2>&1; then
    echo 'PASS: database migration, API readiness, and Web root response'
    exit 0
  fi
  if [[ "$(docker inspect -f '{{.State.Running}}' "$server")" != true ]]; then
    break
  fi
  sleep 2
done
echo 'FAIL: server did not pass startup checks'
docker logs "$server" 2>&1 | python3 -c '
import sys
for line in sys.stdin:
    if any(word in line.lower() for word in ("token", "secret", "password", "bootstrap")):
        print("[sensitive startup message omitted]")
    else:
        print(line, end="")
'
exit 1
