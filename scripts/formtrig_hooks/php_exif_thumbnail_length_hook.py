#!/usr/bin/env python3
"""FORMTRIG repair hook for EXIF thumbnail-length exploration.

This is a target-specific repair probe for PHP003-style EXIF thumbnail state.
It mutates the standard TIFF IFD1 JPEGInterchangeFormatLength tag without
changing the harness or oracle.
"""

from __future__ import annotations

import sys


MAX_OUTPUT_LEN = 1 << 20
JPEG_APP1 = b"\xff\xe1"
EXIF_HEADER = b"Exif\x00\x00"
TAG_JPEG_OFFSET = 0x0201
TAG_JPEG_LENGTH = 0x0202


def u16(data: bytes | bytearray, offset: int, endian: str) -> int:
    return int.from_bytes(data[offset : offset + 2], endian)


def u32(data: bytes | bytearray, offset: int, endian: str) -> int:
    return int.from_bytes(data[offset : offset + 4], endian)


def put_u16(data: bytearray, offset: int, value: int, endian: str) -> None:
    data[offset : offset + 2] = int(value & 0xFFFF).to_bytes(2, endian)


def put_u32(data: bytearray, offset: int, value: int, endian: str) -> None:
    data[offset : offset + 4] = int(value & 0xFFFFFFFF).to_bytes(4, endian)


def exif_bases(data: bytes | bytearray) -> list[int]:
    bases: list[int] = []
    pos = 0
    while True:
        pos = data.find(EXIF_HEADER, pos)
        if pos < 0:
            return bases
        bases.append(pos + len(EXIF_HEADER))
        pos += 1


def ifd_entries(data: bytes | bytearray, base: int, ifd_offset: int, endian: str) -> tuple[list[int], int]:
    if ifd_offset <= 0 or base + ifd_offset + 2 > len(data):
        return [], 0
    count = u16(data, base + ifd_offset, endian)
    entries_start = base + ifd_offset + 2
    entries_end = entries_start + count * 12
    if entries_end + 4 > len(data):
        return [], 0
    return [entries_start + index * 12 for index in range(count)], u32(data, entries_end, endian)


def tiff_layout(data: bytes | bytearray, base: int) -> tuple[str, int] | None:
    if base + 8 > len(data):
        return None
    order = bytes(data[base : base + 2])
    if order == b"MM":
        endian = "big"
    elif order == b"II":
        endian = "little"
    else:
        return None
    if u16(data, base + 2, endian) != 0x2A:
        return None
    return endian, u32(data, base + 4, endian)


def find_ifd1_thumbnail_tags(data: bytes | bytearray) -> tuple[int, str, int, int | None] | None:
    for base in exif_bases(data):
        layout = tiff_layout(data, base)
        if layout is None:
            continue
        endian, ifd0 = layout
        entries, next_ifd = ifd_entries(data, base, ifd0, endian)
        if not entries or not next_ifd:
            continue
        ifd1_entries, _ = ifd_entries(data, base, next_ifd, endian)
        length_entry = None
        offset_value = None
        for entry in ifd1_entries:
            tag = u16(data, entry, endian)
            if tag == TAG_JPEG_LENGTH:
                length_entry = entry
            elif tag == TAG_JPEG_OFFSET:
                offset_value = u32(data, entry + 8, endian)
        if length_entry is not None:
            return base, endian, length_entry, offset_value
    return None


def write_inline_value(data: bytearray, entry: int, endian: str, value: int) -> bool:
    field_type = u16(data, entry + 2, endian)
    count = u32(data, entry + 4, endian)
    value_offset = entry + 8
    if count != 1:
        return False
    if field_type == 4:
        put_u32(data, value_offset, value, endian)
        return True
    if field_type == 3:
        put_u16(data, value_offset, value, endian)
        return True
    if field_type == 1:
        data[value_offset] = value & 0xFF
        return True
    return False


def mutate(data: bytes, selector: int) -> bytes | None:
    found = find_ifd1_thumbnail_tags(data)
    if found is None:
        return None
    base, endian, length_entry, offset_value = found
    out = bytearray(data)
    new_lengths = [1, 2, 3, 4, 0, 8]
    if not write_inline_value(out, length_entry, endian, new_lengths[selector % len(new_lengths)]):
        return None
    if offset_value is not None:
        thumb = base + offset_value
        if 0 <= thumb < len(out):
            marker = b"\xff\xd8\xff"
            out[thumb : min(len(out), thumb + len(marker))] = marker[: max(0, min(len(out) - thumb, len(marker)))]
    return bytes(out[:MAX_OUTPUT_LEN])


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

    selector = op + sample * 17
    out = mutate(mutated, selector)
    if out is None:
        out = mutate(original, selector)
    if out is None:
        out = mutated

    with open(out_path, "wb") as handle:
        handle.write(out[:MAX_OUTPUT_LEN])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
