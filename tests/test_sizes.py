import pytest

from dockerhygiene.sizes import format_size, parse_size


@pytest.mark.parametrize(
    "text, expected",
    [
        ("0B", 0),
        ("512B", 512),
        ("1.6kB", 1600),
        ("127.1MB", 127_100_000),
        ("3.346GB", 3_346_000_000),
        ("56.52GB", 56_520_000_000),
        ("1TB", 1_000_000_000_000),
        (" 7.755GB ", 7_755_000_000),
    ],
)
def test_parse_size(text, expected):
    assert parse_size(text) == expected


@pytest.mark.parametrize("bad", ["", "GB", "12", "1.2.3GB", "5 GiB", "-1GB"])
def test_parse_size_rejects_garbage(bad):
    with pytest.raises(ValueError):
        parse_size(bad)


@pytest.mark.parametrize(
    "n, expected",
    [(0, "0B"), (999, "999B"), (1000, "1kB"), (3_346_000_000, "3.35GB"), (63_600_000_000, "63.6GB")],
)
def test_format_size(n, expected):
    assert format_size(n) == expected


def test_round_trip():
    for text in ["1.5kB", "25.21GB", "63.6GB"]:
        assert format_size(parse_size(text)) == text


def test_negative_size_rejected():
    with pytest.raises(ValueError):
        format_size(-1)
