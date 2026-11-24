"""A small teaching linter for Dockerfiles.

It is not a replacement for hadolint (CI runs hadolint too). Each rule maps to
one lesson in the course, so the message says *why*, not only *what*.

Rule ids:

    DH001 error    base image has no tag or uses :latest
    DH002 error    container runs as root (no USER, or last USER is root)
    DH003 warning  ADD used for a local file (use COPY)
    DH004 warning  apt-get install without --no-install-recommends
    DH005 warning  apt-get install without cleaning /var/lib/apt/lists in the same RUN
    DH006 error    secret-looking ENV/ARG with a value baked into the image
    DH007 warning  CMD/ENTRYPOINT in shell form (signals do not reach your app)
    DH008 warning  pip install without --no-cache-dir
    DH009 warning  'COPY . .' (or 'ADD . .') before installing dependencies (breaks layer cache)
    DH010 info     no HEALTHCHECK
    DH011 warning  no .dockerignore next to the build context
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

SEVERITY_ORDER = {"info": 0, "warning": 1, "error": 2}

_SECRET_NAME = re.compile(r"(PASSWORD|PASSWD|SECRET|TOKEN|API_?KEY|PRIVATE_?KEY|ACCESS_?KEY)", re.I)
_DEP_INSTALL = re.compile(
    r"\b(pip3?\s+install\b[^&;|]*\s(-r|--requirement|\.)(\s|$)|npm\s+(ci|install)|yarn\s+install|"
    r"poetry\s+install|uv\s+sync|bundle\s+install|go\s+mod\s+download|mvn\s+.*dependency)"
)


@dataclass(frozen=True)
class Instruction:
    line: int
    keyword: str
    args: str


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    line: int
    message: str


def parse(text: str) -> list[Instruction]:
    """Split a Dockerfile into instructions, joining backslash continuations."""
    instructions: list[Instruction] = []
    buffer = ""
    start = 0
    for number, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if not buffer and (not stripped or stripped.startswith("#")):
            continue
        if buffer and stripped.startswith("#"):
            continue  # comment lines inside a continuation are ignored by Docker
        if not buffer:
            start = number
        if stripped.endswith("\\"):
            buffer += stripped[:-1] + " "
            continue
        buffer += stripped
        parts = buffer.split(None, 1)
        keyword = parts[0].upper()
        args = parts[1] if len(parts) > 1 else ""
        instructions.append(Instruction(start, keyword, args))
        buffer = ""
    if buffer:
        parts = buffer.split(None, 1)
        instructions.append(Instruction(start, parts[0].upper(), parts[1] if len(parts) > 1 else ""))
    return instructions


def _from_image(args: str) -> tuple[str, str | None]:
    """Return (image, stage_alias) from FROM arguments."""
    tokens = [t for t in args.split() if not t.startswith("--")]
    image = tokens[0] if tokens else ""
    alias = None
    if len(tokens) >= 3 and tokens[1].upper() == "AS":
        alias = tokens[2].lower()
    return image, alias


def _is_exec_form(args: str) -> bool:
    return args.strip().startswith("[")


def check(text: str, context_dir: Path | None = None) -> list[Finding]:
    instructions = parse(text)
    findings: list[Finding] = []
    stages: set[str] = set()
    stage_users: dict[str, str | None] = {}
    current_stage: str | None = None
    pip_cache_off = False
    last_from_line = 0
    user_in_final_stage: str | None = None
    has_healthcheck = False
    copied_all_at: int | None = None

    for ins in instructions:
        kw, args = ins.keyword, ins.args

        if kw == "FROM":
            image, alias = _from_image(args)
            last_from_line = ins.line
            copied_all_at = None
            name = image.lower()
            is_stage = name in stages
            # A stage built FROM an earlier stage inherits its USER and ENV.
            user_in_final_stage = stage_users.get(name) if is_stage else None
            if not is_stage:
                pip_cache_off = False
            current_stage = alias
            if alias:
                stages.add(alias)
                stage_users[alias] = user_in_final_stage
            if name == "scratch" or is_stage or "$" in image or "@sha256:" in image:
                continue
            last_part = image.rsplit("/", 1)[-1]
            if ":" not in last_part:
                findings.append(Finding("DH001", "error", ins.line,
                    f"'{image}' has no tag, so it means :latest. Pin a version (and a digest for "
                    "production) so the same Dockerfile builds the same image next month."))
            elif last_part.endswith(":latest"):
                findings.append(Finding("DH001", "error", ins.line,
                    f"'{image}' uses :latest, which moves. Pin a version."))

        elif kw == "USER":
            user_in_final_stage = args.split(":")[0].strip()
            if current_stage:
                stage_users[current_stage] = user_in_final_stage

        elif kw == "ADD":
            sources = [t for t in args.split() if not t.startswith("--")][:-1]
            if sources and sources[0] in (".", "./"):
                copied_all_at = ins.line
            local = [s for s in sources if not re.match(r"^(https?://|git@)", s)
                     and not re.search(r"\.(tar|tgz|tar\.\w+)$", s)]
            if local:
                findings.append(Finding("DH003", "warning", ins.line,
                    "ADD can fetch URLs and auto-extract archives, which surprises people. "
                    "For plain local files use COPY."))

        elif kw == "RUN":
            if re.search(r"\bapt-get\s+(-\S+\s+)*install\b", args):
                if "--no-install-recommends" not in args:
                    findings.append(Finding("DH004", "warning", ins.line,
                        "apt-get install pulls 'recommended' packages too. Add "
                        "--no-install-recommends to keep the image small."))
                if "/var/lib/apt/lists" not in args:
                    findings.append(Finding("DH005", "warning", ins.line,
                        "Remove /var/lib/apt/lists/* in the SAME RUN. Deleting it in a later "
                        "layer does not make the image smaller."))
            if (re.search(r"\bpip3?\s+install\b", args) and "--no-cache-dir" not in args
                    and "--mount=type=cache" not in args and not pip_cache_off):
                findings.append(Finding("DH008", "warning", ins.line,
                    "pip keeps a download cache inside the layer. Use --no-cache-dir (or a "
                    "BuildKit cache mount)."))
            if copied_all_at is not None and _DEP_INSTALL.search(args):
                findings.append(Finding("DH009", "warning", copied_all_at,
                    "'COPY . .' comes before the dependency install, so any code change "
                    "re-installs every dependency. Copy the lock/requirements file first, "
                    "install, then copy the rest."))
                copied_all_at = None

        elif kw == "COPY":
            tokens = [t for t in args.split() if not t.startswith("--")]
            if len(tokens) >= 2 and tokens[0] in (".", "./") and "--from" not in args:
                copied_all_at = ins.line

        elif kw in ("ENV", "ARG"):
            for name, value in _assignments(kw, args):
                if name.upper() == "PIP_NO_CACHE_DIR" and value.lower() in ("1", "true", "on", "yes"):
                    pip_cache_off = True
                # NAME_FILE / NAME_PATH point at a secret file: that is the safe pattern.
                if (_SECRET_NAME.search(name) and value
                        and not re.search(r"_(FILE|PATH|DIR)$", name, re.I)
                        and not value.startswith("/run/secrets/")):
                    findings.append(Finding("DH006", "error", ins.line,
                        f"{kw} {name} puts a secret into the image history, where anyone with "
                        "the image can read it ('docker history'). Use a BuildKit secret "
                        "mount at build time or a runtime secret/env var."))

        elif kw in ("CMD", "ENTRYPOINT"):
            if not _is_exec_form(args):
                findings.append(Finding("DH007", "warning", ins.line,
                    f"{kw} in shell form runs under /bin/sh -c, so 'docker stop' sends SIGTERM "
                    "to the shell, not your app. Use exec form: "
                    f'{kw} ["prog", "arg"].'))

        elif kw == "HEALTHCHECK":
            has_healthcheck = args.strip().upper() != "NONE"

    if last_from_line:
        if user_in_final_stage is None or user_in_final_stage in ("root", "0"):
            findings.append(Finding("DH002", "error", last_from_line,
                "The final stage runs as root. Create a user and add USER, so a bug in the "
                "app does not hand an attacker root inside the container."))
        if not has_healthcheck:
            findings.append(Finding("DH010", "info", last_from_line,
                "No HEALTHCHECK. Docker can only tell 'process running', not 'app working'. "
                "Fine if your orchestrator does its own probes (Kubernetes ignores this)."))

    if context_dir is not None and not (context_dir / ".dockerignore").exists():
        findings.append(Finding("DH011", "warning", 0,
            "No .dockerignore. The whole folder (.git, venvs, data, secrets) is sent to the "
            "builder and can end up in the image via COPY."))

    findings.sort(key=lambda f: (f.line, f.rule))
    return findings


def _assignments(keyword: str, args: str) -> list[tuple[str, str]]:
    """Return (name, value) pairs from ENV or ARG arguments."""
    args = args.strip()
    if not args:
        return []
    if keyword == "ARG":
        # ARG can declare several names: ARG A=1 B C="x y"
        return [(name, value.strip("'\""))
                for name, value in re.findall(r'(\w+)(?:=("[^"]*"|\'[^\']*\'|\S*))?', args)]
    if "=" not in args.split(None, 1)[0]:
        # legacy form: ENV NAME value
        parts = args.split(None, 1)
        return [(parts[0], parts[1] if len(parts) > 1 else "")]
    pairs = []
    for token in re.findall(r'(\w+)=("[^"]*"|\'[^\']*\'|\S*)', args):
        pairs.append((token[0], token[1].strip("'\"")))
    return pairs


def worst(findings: list[Finding]) -> str | None:
    if not findings:
        return None
    return max(findings, key=lambda f: SEVERITY_ORDER[f.severity]).severity


def render(path: str, findings: list[Finding]) -> str:
    if not findings:
        return f"{path}: no findings"
    lines = []
    for f in findings:
        where = f"{path}:{f.line}" if f.line else path
        lines.append(f"{where}: {f.rule} [{f.severity}] {f.message}")
    return "\n".join(lines)
