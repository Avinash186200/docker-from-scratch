from pathlib import Path

import pytest

from dockerhygiene.cli import main
from dockerhygiene.dockerfile_check import check, parse, worst

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"

GOOD_TAIL = 'USER app\nHEALTHCHECK CMD ["true"]\nCMD ["python", "app.py"]\n'


def rules(text, context=None):
    return [f.rule for f in check(text, context)]


def test_parse_joins_continuations_and_skips_comments():
    text = "FROM python:3.11-slim\n# comment\nRUN a \\\n  # inner comment\n  && b\n"
    ins = parse(text)
    assert [i.keyword for i in ins] == ["FROM", "RUN"]
    assert ins[1].line == 3 and "a" in ins[1].args and "&& b" in ins[1].args


def test_good_example_is_clean():
    text = (EXAMPLES / "Dockerfile").read_text()
    assert check(text, EXAMPLES) == []


def test_multistage_example_is_clean():
    text = (EXAMPLES / "multistage.Dockerfile").read_text()
    assert check(text, EXAMPLES) == []


def test_bad_example_hits_every_rule_except_dockerignore():
    # DH011 (.dockerignore) is about the folder, not the file: tested separately.
    text = (EXAMPLES / "bad.Dockerfile").read_text()
    found = set(rules(text, EXAMPLES))
    assert {"DH001", "DH002", "DH003", "DH004", "DH005", "DH006", "DH007", "DH008",
            "DH009", "DH010"} <= found


@pytest.mark.parametrize(
    "from_line, flagged",
    [
        ("FROM python", True),
        ("FROM python:latest", True),
        ("FROM registry.example.com:5000/team/app", True),
        ("FROM registry.example.com:5000/team/app:1.2", False),
        ("FROM python:3.11-slim", False),
        ("FROM python@sha256:" + "a" * 64, False),
        ("FROM scratch", False),
        ("FROM ${BASE_IMAGE}", False),
        ("FROM --platform=linux/amd64 python:3.11", False),
    ],
)
def test_dh001_tags(from_line, flagged):
    assert ("DH001" in rules(from_line + "\n" + GOOD_TAIL)) is flagged


def test_stage_names_are_not_images():
    text = "FROM golang:1.22 AS build\nRUN go build\nFROM build AS test\nFROM gcr.io/distroless/static:nonroot\n" + GOOD_TAIL
    assert "DH001" not in rules(text)


def test_dh002_root_user():
    assert "DH002" in rules("FROM python:3.11\nCMD [\"x\"]\n")
    assert "DH002" in rules("FROM python:3.11\nUSER app\nUSER root\nCMD [\"x\"]\n")
    assert "DH002" in rules("FROM python:3.11\nUSER 0:0\nCMD [\"x\"]\n")
    assert "DH002" not in rules("FROM python:3.11\nUSER 10001:10001\nCMD [\"x\"]\n")


def test_dh002_only_final_stage_counts():
    text = "FROM python:3.11 AS build\nUSER app\nFROM python:3.11-slim\nCMD [\"x\"]\n"
    assert "DH002" in rules(text)


def test_dh002_stage_inherits_user_from_parent_stage():
    text = "FROM python:3.11-slim AS base\nUSER 10001\nFROM base\nCMD [\"x\"]\n"
    assert "DH002" not in rules(text)
    text_root = "FROM python:3.11-slim AS base\nFROM base\nCMD [\"x\"]\n"
    assert "DH002" in rules(text_root)


def test_dh003_add_vs_copy():
    assert "DH003" in rules("FROM a:1\nADD app.py /app/\n" + GOOD_TAIL)
    assert "DH003" not in rules("FROM a:1\nADD https://example.com/x.tgz /tmp/\n" + GOOD_TAIL)
    assert "DH003" not in rules("FROM a:1\nADD rootfs.tar.gz /\n" + GOOD_TAIL)


def test_dh004_dh005_apt():
    bad = "FROM debian:12\nRUN apt-get update && apt-get install -y curl\n" + GOOD_TAIL
    good = ("FROM debian:12\nRUN apt-get update && apt-get install -y --no-install-recommends curl "
            "&& rm -rf /var/lib/apt/lists/*\n" + GOOD_TAIL)
    assert {"DH004", "DH005"} <= set(rules(bad))
    assert not {"DH004", "DH005"} & set(rules(good))


@pytest.mark.parametrize(
    "line, flagged",
    [
        ("ENV DB_PASSWORD=hunter2", True),
        ("ENV GITHUB_TOKEN hunter2", True),
        ("ARG API_KEY=abc", True),
        ('ENV A=1 SECRET_KEY="x y"', True),
        ("ARG API_KEY", False),          # declared without a value: fine
        ("ENV PASSWORD_FILE=", False),   # empty value
        ("ENV LOG_LEVEL=info", False),
        ("ENV POSTGRES_PASSWORD_FILE=/run/secrets/db_password", False),  # the safe pattern
        ("ENV DB_PASSWORD=/run/secrets/db", False),
        ("ARG VERSION=1 API_KEY=abc", True),  # second pair on one line
        ("ARG A B C", False),
    ],
)
def test_dh006_secrets(line, flagged):
    assert ("DH006" in rules("FROM a:1\n" + line + "\n" + GOOD_TAIL)) is flagged


def test_dh007_shell_form():
    assert "DH007" in rules("FROM a:1\nUSER app\nHEALTHCHECK CMD [\"true\"]\nCMD python app.py\n")
    assert "DH007" in rules("FROM a:1\nUSER app\nHEALTHCHECK CMD [\"true\"]\nENTRYPOINT ./run.sh\n")
    assert "DH007" not in rules("FROM a:1\n" + GOOD_TAIL)


def test_dh008_pip_cache():
    assert "DH008" in rules("FROM a:1\nRUN pip install flask==3.0.0\n" + GOOD_TAIL)
    assert "DH008" not in rules("FROM a:1\nRUN pip install --no-cache-dir flask==3.0.0\n" + GOOD_TAIL)
    assert "DH008" not in rules(
        "FROM a:1\nRUN --mount=type=cache,target=/root/.cache/pip pip install flask==3.0.0\n" + GOOD_TAIL)
    assert "DH008" not in rules(
        "FROM a:1\nENV PIP_NO_CACHE_DIR=1\nRUN pip install flask==3.0.0\n" + GOOD_TAIL)
    # the setting does not carry into a new, unrelated stage
    assert "DH008" in rules(
        "FROM a:1 AS one\nENV PIP_NO_CACHE_DIR=1\nFROM a:1\nRUN pip install flask==3.0.0\n" + GOOD_TAIL)


def test_dh009_copy_order():
    bad = "FROM a:1\nCOPY . .\nRUN pip install --no-cache-dir -r requirements.txt\n" + GOOD_TAIL
    good = ("FROM a:1\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\n"
            "COPY . .\n" + GOOD_TAIL)
    node_bad = "FROM node:20\nCOPY . .\nRUN npm ci\n" + GOOD_TAIL
    assert "DH009" in rules(bad)
    assert "DH009" in rules(node_bad)
    assert "DH009" not in rules(good)


def test_dh009_resets_per_stage():
    text = "FROM a:1 AS one\nCOPY . .\nFROM a:1\nRUN npm ci\n" + GOOD_TAIL
    assert "DH009" not in rules(text)


def test_dh010_healthcheck():
    assert "DH010" in rules("FROM a:1\nUSER app\nCMD [\"x\"]\n")
    assert "DH010" in rules("FROM a:1\nUSER app\nHEALTHCHECK NONE\nCMD [\"x\"]\n")


def test_dh011_dockerignore(tmp_path):
    text = "FROM a:1\n" + GOOD_TAIL
    assert "DH011" in rules(text, tmp_path)
    (tmp_path / ".dockerignore").write_text(".git\n")
    assert "DH011" not in rules(text, tmp_path)


def test_worst_severity():
    assert worst([]) is None
    assert worst(check("FROM a:1\nUSER app\nCMD [\"x\"]\n")) == "info"
    assert worst(check("FROM python\n")) == "error"


def test_cli_exit_codes(capsys):
    assert main(["check", str(EXAMPLES / "Dockerfile")]) == 0
    assert main(["check", str(EXAMPLES / "bad.Dockerfile")]) == 1
    out = capsys.readouterr().out
    assert "no findings" in out and "DH006" in out


def test_cli_fail_on_error_only(tmp_path):
    f = tmp_path / "Dockerfile"
    f.write_text("FROM a:1\nUSER app\nCMD [\"x\"]\n")
    (tmp_path / ".dockerignore").write_text("")
    assert main(["check", str(f), "--fail-on", "info"]) == 1
    assert main(["check", str(f), "--fail-on", "warning"]) == 0
