#!/usr/bin/env bash
# Read-only report of what is using Docker disk space. Deletes nothing.
# Usage: scripts/docker-disk-report.sh
set -euo pipefail

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running, or this user cannot reach the engine." >&2
  exit 1
fi

section() { printf '\n== %s ==\n' "$1"; }

section "docker system df"
docker system df

section "Counts"
printf 'stopped containers : %s\n' "$(docker ps -aq --filter status=exited --filter status=created | wc -l | tr -d ' ')"
printf 'dangling images    : %s\n' "$(docker images -q --filter dangling=true | wc -l | tr -d ' ')"
printf 'all volumes        : %s\n' "$(docker volume ls -q | wc -l | tr -d ' ')"
printf 'unused volumes     : %s\n' "$(docker volume ls -q --filter dangling=true | wc -l | tr -d ' ')"
anon=$(docker volume ls -q --filter dangling=true | grep -cE '^[0-9a-f]{64}$' || true)
printf '  of which anonymous (hash names): %s\n' "$anon"

section "Biggest images (top 10)"
docker images --format '{{.Size}}\t{{.Repository}}:{{.Tag}}\t{{.CreatedSince}}' \
  | sort -h -r | head -10

section "Named volumes not used by any container"
docker volume ls -q --filter dangling=true | grep -vE '^[0-9a-f]{64}$' || echo "(none)"

section "Stopped containers (newest 15)"
docker ps -a --filter status=exited --format '{{.Names}}\t{{.Image}}\t{{.Status}}' | head -15

section "Next step"
echo "docker system df | python -m dockerhygiene.cli df   # suggested cleanup order"
echo "scripts/docker-cleanup.sh                           # dry run of the cleanup"
