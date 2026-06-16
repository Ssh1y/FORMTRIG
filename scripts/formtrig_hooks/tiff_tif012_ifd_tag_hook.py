#!/usr/bin/env python3
"""Typed FORMTRIG mutation hook for Magma TIF012.

The TIF012 trigger is order/state dependent: libtiff must observe a
TransferFunction-derived state before SamplesPerPixel is changed from its
default single-sample state. Plain byte flips rarely make a well-formed IFD
with that ordering, so this hook rewrites the first-IFD pointer to a new IFD
appended at EOF and inserts a TransferFunction entry before SamplesPerPixel.
"""

from __future__ import annotations

import struct
import sys
from dataclasses import dataclass


TIFFTAG_SAMPLESPERPIXEL = 277
TIFFTAG_TRANSFERFUNCTION = 301
TIFF_SHORT = 3


@dataclass(frozen=True)
class TiffEntry:
    tag: int
    typ: int
    count: int
    value: int


def parse_tiff(data: bytes) -> tuple[str, int, list[TiffEntry], int] | None:
    if len(data) < 8:
        return None
    if data[:2] == b"II":
        endian = "<"
    elif data[:2] == b"MM":
        endian = ">"
    else:
        return None
    if struct.unpack(endian + "H", data[2:4])[0] != 42:
        return None
    first_ifd = struct.unpack(endian + "I", data[4:8])[0]
    if first_ifd + 2 > len(data):
        return None
    entry_count = struct.unpack(endian + "H", data[first_ifd : first_ifd + 2])[0]
    table_end = first_ifd + 2 + entry_count * 12 + 4
    if table_end > len(data):
        return None

    entries: list[TiffEntry] = []
    for idx in range(entry_count):
        pos = first_ifd + 2 + idx * 12
        tag, typ, count, value = struct.unpack(endian + "HHII", data[pos : pos + 12])
        entries.append(TiffEntry(tag, typ, count, value))
    next_ifd = struct.unpack(endian + "I", data[table_end - 4 : table_end])[0]
    return endian, first_ifd, entries, next_ifd


def pack_entry(endian: str, entry: TiffEntry) -> bytes:
    return struct.pack(endian + "HHII", entry.tag, entry.typ, entry.count, entry.value)


def transfer_function_payload(endian: str, sample: int) -> bytes:
    values = []
    mode = sample % 3
    for i in range(256):
        if mode == 0:
            value = i * 257
        elif mode == 1:
            value = min(65535, (i * i) & 0xFFFF)
        else:
            value = 65535 - i * 257
        values.append(value)
    return struct.pack(endian + "256H", *values)


def build_tif012_candidate(data: bytes, op: int, sample: int) -> bytes | None:
    parsed = parse_tiff(data)
    if parsed is None:
        return None
    endian, _first_ifd, entries, next_ifd = parsed
    if any(entry.tag == TIFFTAG_TRANSFERFUNCTION for entry in entries):
        return None

    tf_payload = transfer_function_payload(endian, op + sample)
    pad = b"\x00" if len(data) % 2 else b""
    new_ifd_offset = len(data) + len(pad)

    insert_at = None
    for idx, entry in enumerate(entries):
        if entry.tag == TIFFTAG_SAMPLESPERPIXEL:
            insert_at = idx
            break
    if insert_at is None:
        insert_at = min(len(entries), 4)
        spp_value = 3 if endian == "<" else 3 << 16
        entries.insert(insert_at, TiffEntry(TIFFTAG_SAMPLESPERPIXEL, TIFF_SHORT, 1, spp_value))
        insert_at += 1

    new_entry_count = len(entries) + 1
    tf_offset = new_ifd_offset + 2 + new_entry_count * 12 + 4
    tf_entry = TiffEntry(TIFFTAG_TRANSFERFUNCTION, TIFF_SHORT, 256, tf_offset)
    rewritten_entries = entries[:insert_at] + [tf_entry] + entries[insert_at:]

    header = bytearray(data)
    header[4:8] = struct.pack(endian + "I", new_ifd_offset)

    new_ifd = bytearray()
    new_ifd += struct.pack(endian + "H", len(rewritten_entries))
    for entry in rewritten_entries:
        new_ifd += pack_entry(endian, entry)
    new_ifd += struct.pack(endian + "I", next_ifd)

    return bytes(header) + pad + bytes(new_ifd) + tf_payload


def main(argv: list[str]) -> int:
    if len(argv) < 15:
        return 2
    orig_path, mut_path, out_path = argv[1], argv[2], argv[3]
    op = int(argv[8])
    sample = int(argv[9])

    with open(orig_path, "rb") as handle:
        original = handle.read()
    with open(mut_path, "rb") as handle:
        mutated = handle.read()

    candidate = build_tif012_candidate(original, op, sample)
    if candidate is None:
        candidate = mutated

    with open(out_path, "wb") as handle:
        handle.write(candidate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
