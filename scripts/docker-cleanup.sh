#!/usr/bin/env bash
# Docker cleanup with a dry run by default.
#
# Usage:
#   scripts/docker-cleanup.sh                      # dry run, level "safe"
#   scripts/docker-cleanup.sh --level safe --yes   # do it
#   scripts/docker-cleanup.sh --level all          # dry run of the aggressive level
#   scripts/docker-cleanup.sh --level all --yes    # do it (asks you to type DELETE)
#
# Levels:
#   safe : stopped containers, dangling images, build cache older than 7 days
#          (keeps up to 20GB of recent cache), unused anonymous volumes
#   all  : safe + every unused image + every unused volume INCLUDING NAMED ONES
#          (named volumes often hold local databases: back them up first)
#
# Warning: even "safe" deletes the anonymous volumes of stopped containers. A
# database started without a named volume (docker run postgres, no -v) keeps its
# data in such a volume, and it will be gone.
set -euo pipefail

level="safe"
yes="no"
cache_keep="20GB"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --level|--keep-cache)
      if [[ $# -lt 2 ]]; then echo "$1 needs a value" >&2; exit 2; fi
      if [[ "$1" == "--level" ]]; then level="$2"; else cache_keep="$2"; fi
      shift 2 ;;
    --yes) yes="yes"; shift ;;
    -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ "$level" != "safe" && "$level" != "all" ]]; then
  echo "--level must be 'safe' or 'all'" >&2
  exit 2
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running, or this user cannot reach the engine." >&2
  exit 1
fi

# Newer Docker uses --max-used-space; older versions use --keep-storage.
if docker builder prune --help 2>/dev/null | grep -q -- '--max-used-space'; then
  cache_flag="--max-used-space"
else
  cache_flag="--keep-storage"
fi

count() { wc -l | tr -d ' '; }

echo "Level: $level   (dry run: $([[ $yes == yes ]] && echo no || echo yes))"
echo
echo "Before:"
docker system df
echo
echo "Would remove (image and volume counts are lower bounds: removing stopped"
echo "containers first frees more of both):"
printf '  stopped containers      : %s\n' "$(docker ps -aq --filter status=exited --filter status=created | count)"
printf '  dangling images         : %s\n' "$(docker images -q --filter dangling=true | count)"
printf '  build cache             : older than 168h, keeping up to %s\n' "$cache_keep"
printf '  unused anonymous volumes: %s\n' "$(docker volume ls -q --filter dangling=true | grep -cE '^[0-9a-f]{64}$' || true)"
if [[ "$level" == "all" ]]; then
  printf '  unused images (all)     : every image without a container\n'
  printf '  unused NAMED volumes    :\n'
  docker volume ls -q --filter dangling=true | grep -vE '^[0-9a-f]{64}$' | sed 's/^/      /' || echo "      (none)"
fi

if [[ "$yes" != "yes" ]]; then
  echo
  echo "Dry run only. Add --yes to delete."
  exit 0
fi

if [[ "$level" == "all" ]]; then
  echo
  echo "Level 'all' deletes named volumes listed above. Their data is gone for good."
  read -r -p "Type DELETE to continue: " answer
  [[ "$answer" == "DELETE" ]] || { echo "Stopped."; exit 1; }
fi

docker container prune -f
docker image prune -f
docker builder prune -f --filter until=168h "$cache_flag" "$cache_keep"
docker volume prune -f
if [[ "$level" == "all" ]]; then
  docker image prune -a -f
  docker volume prune -a -f
fi

echo
echo "After:"
docker system df
echo
echo "On Docker Desktop the host disk file does not shrink by itself."
echo "See docs/chapters/16-disk-space-and-cleanup.md (fstrim, then compact)."
