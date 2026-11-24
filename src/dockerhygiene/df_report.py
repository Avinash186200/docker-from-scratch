"""Read ``docker system df`` output and turn it into a cleanup plan.

Two input formats are accepted:

1. The default table::

       TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
       Images          62        17        56.52GB   22.99GB (40%)

2. JSON lines from ``docker system df --format '{{json .}}'``.

The plan follows the order that actually frees space: stopped containers first
(they pin images and volumes), then build cache, then images, then volumes
(last, because named volumes may hold data).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .sizes import format_size, parse_size

_TYPES = ("Images", "Containers", "Local Volumes", "Build Cache")
_ROW_RE = re.compile(
    r"^(Images|Containers|Local Volumes|Build Cache)\s+"
    r"(\d+)\s+(\d+)\s+(\S+)\s+(\S+)(?:\s+\((\d+)%\))?\s*$"
)


@dataclass(frozen=True)
class DfRow:
    kind: str
    total: int
    active: int
    size: int
    reclaimable: int


@dataclass(frozen=True)
class Step:
    reason: str
    command: str
    frees_up_to: int
    destructive: bool
    note: str = ""  # qualifies frees_up_to, e.g. "with -a"


def parse_table(text: str) -> list[DfRow]:
    rows = []
    for line in text.splitlines():
        match = _ROW_RE.match(line.strip())
        if match:
            kind, total, active, size, reclaim, _pct = match.groups()
            rows.append(DfRow(kind, int(total), int(active), parse_size(size), parse_size(reclaim)))
    if not rows:
        raise ValueError("no 'docker system df' rows found")
    return rows


def parse_json_lines(text: str) -> list[DfRow]:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        item = json.loads(line)
        reclaim = item["Reclaimable"].split(" ")[0]
        rows.append(
            DfRow(
                item["Type"],
                int(item["TotalCount"]),
                int(item["Active"]),
                parse_size(item["Size"]),
                parse_size(reclaim),
            )
        )
    if not rows:
        raise ValueError("no JSON rows found")
    return rows


def parse(text: str) -> list[DfRow]:
    """Parse either format."""
    if text.lstrip().startswith("{"):
        return parse_json_lines(text)
    return parse_table(text)


def plan(rows: list[DfRow], build_cache_keep_gb: float = 20.0) -> list[Step]:
    """Return cleanup steps, safest and most useful first."""
    by_kind = {row.kind: row for row in rows}
    steps: list[Step] = []

    containers = by_kind.get("Containers")
    stopped = containers.total - containers.active if containers else 0
    if containers and stopped > 0:
        steps.append(
            Step(
                reason=(
                    f"{stopped} stopped container(s). They hold their images and volumes "
                    "'in use', so the RECLAIMABLE numbers for images and volumes look smaller "
                    "than they really are until these are removed."
                ),
                command="docker container prune",
                frees_up_to=containers.reclaimable,
                destructive=True,
            )
        )

    cache = by_kind.get("Build Cache")
    if cache and cache.size > 0:
        keep = int(build_cache_keep_gb * 1000**3)
        if cache.size > keep:
            steps.append(
                Step(
                    reason=(
                        f"Build cache is {format_size(cache.size)}. It is only a speed-up and is "
                        "rebuilt on the next build. Keep a budget instead of deleting it all. "
                        "(Older Docker versions call this flag --keep-storage; run "
                        "'docker builder prune --help' to see which one you have.)"
                    ),
                    command=f"docker builder prune --max-used-space {int(build_cache_keep_gb)}GB",
                    frees_up_to=cache.size - keep,
                    destructive=False,
                )
            )

    images = by_kind.get("Images")
    if images and images.total > images.active:
        steps.append(
            Step(
                reason=(
                    f"{images.total - images.active} image(s) not used by any container. "
                    "Start with dangling ones (no tag); add -a only if you can pull or rebuild "
                    "the rest."
                ),
                command="docker image prune   # all unused, if you can re-pull: docker image prune -a",
                frees_up_to=images.reclaimable,
                destructive=True,
                note="with -a",
            )
        )

    volumes = by_kind.get("Local Volumes")
    if volumes and volumes.total > volumes.active:
        steps.append(
            Step(
                reason=(
                    f"{volumes.total - volumes.active} volume(s) not attached to a container. "
                    "Since Docker Engine 23, 'volume prune' removes only anonymous volumes; "
                    "'-a' also removes named ones. Named volumes often hold databases, so "
                    "check them before using -a."
                ),
                command="docker volume prune   # named too, only after checking: docker volume prune -a",
                frees_up_to=volumes.reclaimable,
                destructive=True,
                note="with -a",
            )
        )
    return steps


def render(rows: list[DfRow], steps: list[Step]) -> str:
    total = sum(row.size for row in rows)
    lines = ["Docker disk usage", "-----------------"]
    for row in rows:
        lines.append(
            f"{row.kind:<14} total={row.total:<5} active={row.active:<5} "
            f"size={format_size(row.size):<9} reclaimable={format_size(row.reclaimable)}"
        )
    lines.append(f"{'All':<14} size={format_size(total)}")
    lines.append("")
    if not steps:
        lines.append("Nothing worth cleaning.")
        return "\n".join(lines)
    lines.append("Cleanup plan (run in this order, re-check 'docker system df' after each):")
    for i, step in enumerate(steps, 1):
        tag = "deletes data" if step.destructive else "cache only"
        lines.append(f"{i}. [{tag}] {step.command}")
        qualifier = f" ({step.note})" if step.note else ""
        lines.append(f"   frees up to {format_size(step.frees_up_to)}{qualifier}. {step.reason}")
    lines.append("")
    lines.append(
        "On Docker Desktop (Windows/macOS) pruning frees space inside the VM disk. "
        "The disk file on the host does not shrink by itself: see chapter 16."
    )
    return "\n".join(lines)
