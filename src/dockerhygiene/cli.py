"""Command line entry point.

    python -m dockerhygiene.cli df [FILE]          # FILE or stdin: 'docker system df' output
    python -m dockerhygiene.cli check Dockerfile   # lint a Dockerfile
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import df_report, dockerfile_check


def _cmd_df(args: argparse.Namespace) -> int:
    text = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    rows = df_report.parse(text)
    steps = df_report.plan(rows, build_cache_keep_gb=args.keep_cache_gb)
    print(df_report.render(rows, steps))
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    path = Path(args.dockerfile)
    context = Path(args.context) if args.context else path.parent
    findings = dockerfile_check.check(path.read_text(encoding="utf-8"), context_dir=context)
    print(dockerfile_check.render(str(args.dockerfile), findings))
    worst = dockerfile_check.worst(findings)
    if worst is None:
        return 0
    order = dockerfile_check.SEVERITY_ORDER
    return 1 if order[worst] >= order[args.fail_on] else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dockerhygiene")
    sub = parser.add_subparsers(dest="command", required=True)

    p_df = sub.add_parser("df", help="turn 'docker system df' output into a cleanup plan")
    p_df.add_argument("file", nargs="?", help="saved output; reads stdin if omitted")
    p_df.add_argument("--keep-cache-gb", type=float, default=20.0,
                      help="build cache budget to keep (default 20)")
    p_df.set_defaults(func=_cmd_df)

    p_check = sub.add_parser("check", help="lint a Dockerfile against the course rules")
    p_check.add_argument("dockerfile")
    p_check.add_argument("--context", help="build context folder (default: Dockerfile folder)")
    p_check.add_argument("--fail-on", choices=["info", "warning", "error"], default="warning")
    p_check.set_defaults(func=_cmd_check)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
