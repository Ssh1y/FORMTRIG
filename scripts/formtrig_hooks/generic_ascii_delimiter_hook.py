#!/usr/bin/env python3
"""Target-agnostic FORMTRIG external typed-mutation hook.

This hook is intentionally weaker than target-specific repair hooks. It uses
the range/off/op/sample parameters supplied by the native FORMTRIG typed stage
to try generic delimiter and byte-window edits, without parsing a target file
format or constructing vulnerability-specific state.
"""

from __future__ import annotations

import sys


MAX_OUTPUT_LEN = 4096
DELIMITERS = [b"/", b".", b"_", b"-", b":", b"\x00", b"\n"]


def clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(value, hi))


def useful_window(data: bytes, start: int, span: int, off: int) -> bytes:
    if not data:
        return b"A"
    start = clamp(start, 0, len(data))
    end = clamp(start + max(span, 1), start + 1, len(data))
    if start < end:
        window = data[start:end]
    else:
        left = clamp(off - 4, 0, len(data))
        right = clamp(off + 4, left + 1, len(data))
        window = data[left:right]
    cleaned = bytes(
        byte
        for byte in window[:24]
        if byte in (45, 46, 47, 58, 95) or 48 <= byte <= 57 or 65 <= byte <= 90 or 97 <= byte <= 122
    )
    return cleaned or b"A"


def mutate(data: bytes, start: int, span: int, off: int, op: int, sample: int) -> bytes:
    if not data:
        return DELIMITERS[sample % len(DELIMITERS)] + b"A"
    off = clamp(off, 0, len(data))
    start = clamp(start, 0, len(data))
    span = max(span, 1)
    delimiter = DELIMITERS[(op + sample) % len(DELIMITERS)]
    window = useful_window(data, start, span, off)
    selector = op % 6

    if selector == 0:
        out = data[:off] + delimiter + data[off:]
    elif selector == 1:
        out = data[:off] + delimiter + window + delimiter + data[off:]
    elif selector == 2:
        replace_end = clamp(off + 1, off, len(data))
        out = data[:off] + delimiter + data[replace_end:]
    elif selector == 3:
        delete_end = clamp(off + 1 + sample % 4, off + 1, len(data))
        out = data[:off] + data[delete_end:]
    elif selector == 4:
        range_end = clamp(start + min(span, 16), start, len(data))
        out = data[:range_end] + delimiter + data[range_end:]
    else:
        repeat = 1 + (sample % 3)
        out = data[:off] + (window + delimiter) * repeat + data[off:]

    return out[:MAX_OUTPUT_LEN] or data[:1]


def main(argv: list[str]) -> int:
    if len(argv) < 15:
        return 2
    orig_path, mut_path, out_path = argv[1], argv[2], argv[3]
    start = int(argv[5])
    span = int(argv[6])
    off = int(argv[7])
    op = int(argv[8])
    sample = int(argv[9])

    with open(orig_path, "rb") as handle:
        original = handle.read()
    with open(mut_path, "rb") as handle:
        mutated = handle.read()

    source = mutated if mutated != original else original
    out = mutate(source, start, span, off, op, sample)
    if out == original:
        out = mutated

    with open(out_path, "wb") as handle:
        handle.write(out[:MAX_OUTPUT_LEN])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
