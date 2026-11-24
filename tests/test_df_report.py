from pathlib import Path

import pytest

from dockerhygiene import df_report
from dockerhygiene.cli import main

FIXTURES = Path(__file__).parent / "fixtures"
BEFORE = (FIXTURES / "system_df_before.txt").read_text()
AFTER = (FIXTURES / "system_df_after.jsonl").read_text()


def test_parse_table_from_the_real_incident():
    rows = {r.kind: r for r in df_report.parse(BEFORE)}
    assert rows["Images"].total == 62 and rows["Images"].active == 17
    assert rows["Containers"].reclaimable == 3_346_000_000
    assert rows["Local Volumes"].total == 270
    assert rows["Build Cache"].size == 63_600_000_000
    assert sum(r.size for r in rows.values()) == 148_676_000_000


def test_parse_json_lines():
    rows = df_report.parse(AFTER)
    assert [r.kind for r in rows] == ["Images", "Containers", "Local Volumes", "Build Cache"]
    assert all(r.size == 0 for r in rows)


def test_json_with_percentage_in_reclaimable():
    line = '{"Active":"17","Reclaimable":"22.99GB (40%)","Size":"56.52GB","TotalCount":"62","Type":"Images"}'
    (row,) = df_report.parse(line)
    assert row.reclaimable == 22_990_000_000


def test_plan_removes_stopped_containers_first():
    steps = df_report.plan(df_report.parse(BEFORE))
    assert steps[0].command == "docker container prune"
    assert "stopped container" in steps[0].reason
    commands = " ".join(s.command for s in steps)
    assert "builder prune --max-used-space 20GB" in commands
    assert "image prune" in commands and "volume prune" in commands


def test_build_cache_step_keeps_a_budget():
    steps = df_report.plan(df_report.parse(BEFORE), build_cache_keep_gb=10)
    cache = next(s for s in steps if "builder" in s.command)
    assert cache.frees_up_to == 63_600_000_000 - 10_000_000_000
    assert cache.destructive is False


def test_volume_step_explains_named_vs_anonymous():
    steps = df_report.plan(df_report.parse(BEFORE))
    vol = next(s for s in steps if "volume" in s.command)
    assert "anonymous" in vol.reason and "-a" in vol.reason


def test_empty_docker_needs_nothing():
    rows = df_report.parse(AFTER)
    assert df_report.plan(rows) == []
    assert "Nothing worth cleaning" in df_report.render(rows, [])


def test_garbage_input_raises():
    with pytest.raises(ValueError):
        df_report.parse("hello world")


def test_cli_df(capsys):
    assert main(["df", str(FIXTURES / "system_df_before.txt")]) == 0
    out = capsys.readouterr().out
    assert "1. [deletes data] docker container prune" in out
    assert "All            size=148.68GB" in out
    assert "chapter 16" in out
