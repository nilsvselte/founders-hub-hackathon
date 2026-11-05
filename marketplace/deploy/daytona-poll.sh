#!/usr/bin/env bash
set -euo pipefail
umask 077

root=${STANDBYROOM_DEPLOY_ROOT:-"$HOME/.local/share/standbyroom"}
runner=$(cd -- "$(dirname -- "$0")" && pwd)/daytona-release.sh
repo=https://github.com/nilsvselte/founders-hub-hackathon.git
marker=http://127.0.0.1:3000/.well-known/standbyroom-release.json
export GIT_TERMINAL_PROMPT=0

mkdir -p "$root"
exec 8>"$root/poll.lock"
flock -n 8

deploy_main() {
  local head live
  head=$(timeout 30 git ls-remote --exit-code "$repo" refs/heads/main | awk '$2 == "refs/heads/main" {print $1}') || return 1
  [[ "$head" =~ ^[0-9a-f]{40}$ ]] || return 1
  live=$(curl -fsS --max-time 5 -H 'Cache-Control: no-cache' "$marker" 2>/dev/null |
    python3 -c 'import json, sys; print(json.load(sys.stdin)["sha"])' 2>/dev/null) || live=
  [[ "$live" != "$head" ]] || return 0
  if [[ -f "$root/failed-release" && $(cat "$root/failed-release") == "$head" ]]; then
    return 0
  fi

  printf 'Staging main revision %s.\n' "$head"
  if ! bash "$runner" "$head" 8>&-; then
    printf '%s\n' "$head" >"$root/failed-release"
    printf 'Release %s failed. Fix it on main or clear failed-release to retry.\n' "$head" >&2
    return 1
  fi
  rm -f -- "$root/failed-release"
}

check_once() {
  bash "$runner" --resume 8>&- || return 1
  deploy_main
}

if [[ ${1:-} == --once ]]; then
  check_once
  exit
fi

while true; do
  if check_once; then
    sleep 60
  else
    printf 'Standbyroom deployment check failed; retrying in five minutes.\n' >&2
    sleep 300
  fi
done
