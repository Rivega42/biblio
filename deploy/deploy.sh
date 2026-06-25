#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Biblio — однокомандный деплой на боевой СПб ГТБ.
#
# Запускается ВНУТРИ контейнера LXC 100 «biblio» (там живут git, docker, /opt/biblio).
# С рабочей станции (топология выстрадана 2026-06-23, см. memory prod-reality):
#
#   ssh gh-prod "ssh theatrelib 'pct exec 100 -- bash /opt/biblio/deploy/deploy.sh'"
#
#   theatrelib = pve (ProxyJump gh-prod, ключ theatrelib_access лежит НА gh-prod);
#   pct exec 100 — внутрь контейнера biblio.
#
# Что делает: fetch+reset на origin/<branch> (по умолч. main) → пересборка backend
# (мультистейдж: vite-фронт собирается внутри и dist бэйкается в образ) → up -d →
# ожидание healthy → печать задеплоенного бандла. .env (gitignored) не трогается.
#
# Аргументы:  $1 — ветка (по умолчанию main).
# Коды:       0 — успех (backend healthy); 1 — backend не поднялся здоровым.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO=/opt/biblio
BRANCH="${1:-main}"
COMPOSE=(docker compose -f "$REPO/deploy/docker-compose.yml")

say() { printf '\n\033[1;36m▶ %s\033[0m\n' "$*"; }

say "git fetch+reset → origin/$BRANCH"
git -C "$REPO" fetch origin "$BRANCH" --depth 1
git -C "$REPO" reset --hard FETCH_HEAD
echo "HEAD: $(git -C "$REPO" log --oneline -1)"

say "сборка backend (пересобирает фронт + бэйкает dist)"
"${COMPOSE[@]}" build backend

say "поднимаю контейнеры"
"${COMPOSE[@]}" up -d

say "жду healthy backend"
healthy=0
for _ in $(seq 1 40); do
  line="$("${COMPOSE[@]}" ps --format '{{.Service}} {{.Status}}' 2>/dev/null | grep '^backend' || true)"
  echo "   $line"
  case "$line" in *"(healthy)"*) healthy=1; break;; esac
  sleep 3
done

if [ "$healthy" != 1 ]; then
  printf '\n\033[1;31m✗ backend не стал healthy — смотри логи: docker compose logs backend\033[0m\n'
  exit 1
fi

say "задеплоенный фронт-бандл"
docker exec deploy-proxy-1 curl -fsk https://localhost/ 2>/dev/null | grep -o 'assets/index-[A-Za-z0-9_-]*\.js' || true
docker exec deploy-proxy-1 curl -fsk https://localhost/api/health 2>/dev/null || true

printf '\n\033[1;32m✓ деплой завершён (backend healthy)\033[0m\n'
