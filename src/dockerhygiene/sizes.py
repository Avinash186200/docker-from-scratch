"""Parse and format the human sizes Docker prints, such as ``56.52GB`` or ``1.6kB``.

Docker's CLI uses decimal units (1 kB = 1000 B), not binary ones (1 KiB = 1024 B).
"""

from __future__ import annotations

import re

_UNITS = {
    "B": 1,
    "KB": 1000,
    "MB": 1000**2,
    "GB": 1000**3,
    "TB": 1000**4,
    "PB": 1000**5,
}

_SIZE_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([kKmMgGtTpP]?[bB])\s*$")


def parse_size(text: str) -> int:
    """Return the number of bytes in a Docker size string.

    >>> parse_size("56.52GB")
    56520000000
    >>> parse_size("0B")
    0
    """
    match = _SIZE_RE.match(text)
    if not match:
        raise ValueError(f"not a Docker size: {text!r}")
    number, unit = match.groups()
    return round(float(number) * _UNITS[unit.upper()])


def format_size(n_bytes: int | float) -> str:
    """Format bytes the way Docker does, with up to 2 decimals.

    >>> format_size(3346000000)
    '3.35GB'
    """
    if n_bytes < 0:
        raise ValueError("size cannot be negative")
    for unit in ("B", "kB", "MB", "GB", "TB"):
        if n_bytes < 1000 or unit == "TB":
            if unit == "B":
                return f"{int(n_bytes)}B"
            return f"{n_bytes:.2f}".rstrip("0").rstrip(".") + unit
        n_bytes /= 1000
    raise AssertionError("unreachable")
