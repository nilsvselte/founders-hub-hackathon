#!/usr/bin/env bash
set -euo pipefail
umask 077

root=${STANDBYROOM_DEPLOY_ROOT:-"$HOME/.local/share/standbyroom"}
runtime_env=${STANDBYROOM_RUNTIME_ENV:-"$HOME/.config/standbyroom/runtime.env"}
repo=https://github.com/nilsvselte/founders-hub-hackathon.git
web_url=http://127.0.0.1:3000
api_url=http://127.0.0.1:8000
marker=/.well-known/standbyroom-release.json

mkdir -p "$root"/{backups,logs,releases}
exec 9>"$root/release.lock"
flock -x 9

# This file is set by the sandbox operator and is outside every Git checkout.
set -a
source "$runtime_env"
set +a
: "${DATABASE_URL:?Set DATABASE_URL in the runtime environment}"
export MARKETPLACE_SECURE_COOKIES=1
unset MARKETPLACE_API_MODE

active=${STANDBYROOM_INITIAL_RELEASE:-}
if [[ -L "$root/current" ]]; then
  active=$(readlink -f "$root/current")
fi

listener() {
  ss -H -ltnp "( sport = :$1 )" | sed -nE 's/.*pid=([0-9]+),.*/\1/p' | sort -u
}

owned_listener() {
  local pid
  pid=$(listener "$1")
  [[ "$pid" =~ ^[0-9]+$ && $(readlink "/proc/$pid/cwd") == "$2" ]]
}

stop_service() {
  local port=$1 cwd=$2 pid
  pid=$(listener "$port")
  [[ -n "$pid" ]] || return 0
  if [[ ! "$pid" =~ ^[0-9]+$ || $(readlink "/proc/$pid/cwd") != "$cwd" ]]; then
    printf 'Unexpected listener on port %s; leaving it alone.\n' "$port" >&2
    return 1
  fi
  kill -TERM "$pid"
  for _ in $(seq 1 40); do
    [[ -z $(listener "$port") ]] && return 0
    sleep .25
  done
  printf 'Port %s did not stop cleanly.\n' "$port" >&2
  return 1
}

wait_http() {
  for _ in $(seq 1 30); do
    curl -fsS --connect-timeout 2 --max-time 5 "$1" >/dev/null 2>&1 && return 0
    sleep .4
  done
  printf 'Readiness check failed at %s.\n' "$1" >&2
  return 1
}

start_api() (
  cd "$1/marketplace/backend"
  export DATABASE_URL="$3"
  # The child must not retain the deployment lock after the runner exits.
  setsid nohup .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$2" \
    >"$root/logs/api-$2.log" 2>&1 </dev/null 9>&- &
)

start_web() (
  cd "$1/marketplace/frontend"
  export NEXT_TELEMETRY_DISABLED=1 MARKETPLACE_API_URL="$api_url"
  setsid nohup ./node_modules/.bin/next start --hostname 0.0.0.0 --port 3000 \
    >"$root/logs/web.log" 2>&1 </dev/null 9>&- &
)

resume_active() {
  [[ -n "$active" && -d "$active/marketplace/backend" && -d "$active/marketplace/frontend" ]] || return 1
  [[ -n $(listener 8000) ]] || start_api "$active" 8000 "$DATABASE_URL" || return 1
  wait_http "$api_url/ready" || return 1
  owned_listener 8000 "$active/marketplace/backend" || return 1
  [[ -n $(listener 3000) ]] || start_web "$active" || return 1
  wait_http "$web_url/api/ready" || return 1
  owned_listener 3000 "$active/marketplace/frontend"
}

if [[ ${1:-} == --resume ]]; then
  resume_active
  exit
fi

sha=${1:-}
if [[ ! "$sha" =~ ^[0-9a-f]{40}$ ]]; then
  printf 'Usage: %s <verified-main-sha>|--resume\n' "$0" >&2
  exit 2
fi
resume_active

if [[ ! -d "$root/source.git" ]]; then
  git init --bare --quiet "$root/source.git"
fi
git --git-dir="$root/source.git" fetch --quiet --depth=1 --no-tags "$repo" refs/heads/main
if [[ $(git --git-dir="$root/source.git" rev-parse FETCH_HEAD) != "$sha" ]]; then
  printf 'Main moved before release %s could be staged.\n' "$sha" >&2
  exit 1
fi

pg_bin=$(pg_config --bindir)
candidate=$(mktemp -d "$root/releases/$sha.XXXXXX")
scratch=
switching=0
ready=0
cleanup() {
  local status=$?
  trap - EXIT
  set +e
  if owned_listener 8001 "$candidate/marketplace/backend"; then
    stop_service 8001 "$candidate/marketplace/backend"
  fi
  if [[ -n "$scratch" ]]; then
    if [[ ! -s "$scratch/data/postmaster.pid" ]] ||
      "$pg_bin/pg_ctl" -D "$scratch/data" -m fast -w stop >/dev/null; then
      rm -rf -- "$scratch"
    fi
  fi
  if (( ! ready )); then
    if (( switching )); then
      if owned_listener 3000 "$candidate/marketplace/frontend"; then
        stop_service 3000 "$candidate/marketplace/frontend"
      fi
      if owned_listener 8000 "$candidate/marketplace/backend"; then
        stop_service 8000 "$candidate/marketplace/backend"
      fi
      if resume_active; then
        printf 'Previous release is healthy again.\n' >&2
      else
        printf 'Previous release could not recover. See logs and the pre-migration backup.\n' >&2
      fi
    fi
    if ! owned_listener 8000 "$candidate/marketplace/backend" &&
      ! owned_listener 8001 "$candidate/marketplace/backend" &&
      ! owned_listener 3000 "$candidate/marketplace/frontend"; then
      rm -rf -- "$candidate"
    fi
  fi
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

git --git-dir="$root/source.git" archive "$sha" | tar -x -C "$candidate"
(
  cd "$candidate/marketplace/backend"
  uv sync --locked --no-dev
)
(
  cd "$candidate/marketplace/frontend"
  mkdir -p public/.well-known
  printf '{"sha":"%s"}\n' "$sha" >"public$marker"
  export NEXT_TELEMETRY_DISABLED=1 MARKETPLACE_API_URL="$api_url"
  corepack pnpm install --frozen-lockfile
  corepack pnpm build
)

if [[ -n $(listener 8001) ]]; then
  printf 'Staging port 8001 is already in use.\n' >&2
  exit 1
fi
scratch=$(mktemp -d /tmp/standbyroom-stage.XXXXXX)
"$pg_bin/initdb" -D "$scratch/data" --auth=trust --no-instructions >/dev/null
"$pg_bin/pg_ctl" -D "$scratch/data" -l "$scratch/pg.log" \
  -o "-c listen_addresses='' -k $scratch" -w start 9>&-
stage_db="postgresql:///postgres?host=$scratch"
pg_dump -Fc "$DATABASE_URL" -f "$scratch/live.dump"
pg_restore --exit-on-error --no-owner --no-privileges -d "$stage_db" "$scratch/live.dump"
start_api "$candidate" 8001 "$stage_db"
wait_http http://127.0.0.1:8001/ready
owned_listener 8001 "$candidate/marketplace/backend"
stop_service 8001 "$candidate/marketplace/backend"

switching=1
stop_service 3000 "$active/marketplace/frontend"
stop_service 8000 "$active/marketplace/backend"
# Migrations on main must support restarting the previous release. The backup
# stays available for operator-led recovery if a migration violates that rule.
backup=$(mktemp "$root/backups/pre-$sha.XXXXXX")
pg_dump -Fc "$DATABASE_URL" -f "$backup"
pg_restore --list "$backup" >/dev/null
start_api "$candidate" 8000 "$DATABASE_URL"
wait_http "$api_url/ready"
owned_listener 8000 "$candidate/marketplace/backend"
start_web "$candidate"
wait_http "$web_url/api/ready"
owned_listener 3000 "$candidate/marketplace/frontend"
[[ $(curl -fsS --max-time 10 "$web_url$marker") == "{\"sha\":\"$sha\"}" ]]
ln -s "$candidate" "$root/.current.$$"
mv -Tf "$root/.current.$$" "$root/current"
ready=1

# Keep the running release and its immediate predecessor.
for old in "$root"/releases/*; do
  [[ "$old" == "$candidate" || "$old" == "$active" ]] || rm -rf -- "$old"
done
for old in "$root"/backups/pre-*; do
  [[ "$old" == "$backup" ]] || rm -f -- "$old"
done
printf 'Running standbyroom release %s.\n' "$sha"
