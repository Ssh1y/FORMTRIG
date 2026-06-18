#!/usr/bin/env python3
"""Generic MP4/ISOBMFF structure mutation hook for FORMTRIG.

The hook is intentionally format-level rather than vulnerability-specific. It
uses the range and operation parameters supplied by FORMTRIG to perturb MP4 box
boundaries, sizes, types, and local payload bytes without embedding a known PoC.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass


MAX_OUTPUT_LEN = 65536
KNOWN_BOX_TYPES = [
    b"ftyp",
    b"moov",
    b"trak",
    b"mdia",
    b"minf",
    b"stbl",
    b"stsd",
    b"stsz",
    b"stco",
    b"mdat",
    b"free",
    b"skip",
]


@dataclass(frozen=True)
class Box:
    start: int
    header: int
    end: int
    size: int
    box_type: bytes


def is_box_type(value: bytes) -> bool:
    return len(value) == 4 and all(32 <= byte <= 126 for byte in value)


def parse_boxes(data: bytes) -> list[Box]:
    boxes: list[Box] = []
    pos = 0
    limit = len(data)
    while pos + 8 <= limit:
        size = int.from_bytes(data[pos : pos + 4], "big")
        box_type = data[pos + 4 : pos + 8]
        header = 8
        if not is_box_type(box_type):
            break
        if size == 1:
            if pos + 16 > limit:
                break
            size = int.from_bytes(data[pos + 8 : pos + 16], "big")
            header = 16
        elif size == 0:
            size = limit - pos
        if size < header or pos + size > limit:
            break
        boxes.append(Box(pos, header, pos + size, size, box_type))
        pos += size
    return boxes


def clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(value, upper))


def pick_box(boxes: list[Box], start: int, span: int, op: int, sample: int) -> Box:
    if not boxes:
        raise ValueError("no boxes")
    span = max(span, 1)
    end = start + span
    overlapping = [box for box in boxes if box.start < end and box.end > start]
    candidates = overlapping or boxes
    return candidates[(op + sample) % len(candidates)]


def put_u32(data: bytearray, off: int, value: int) -> None:
    data[off : off + 4] = value.to_bytes(4, "big")


def make_box(box_type: bytes, payload: bytes) -> bytes:
    payload = payload[: max(0, MAX_OUTPUT_LEN - 8)]
    return (len(payload) + 8).to_bytes(4, "big") + box_type + payload


def useful_payload(data: bytes, box: Box, off: int, sample: int) -> bytes:
    payload_start = box.start + box.header
    payload_end = box.end
    if payload_start < payload_end:
        window_start = clamp(off, payload_start, payload_end)
        window_end = clamp(window_start + 32 + (sample % 32), window_start, payload_end)
        window = data[window_start:window_end] or data[payload_start:payload_end]
    else:
        window = data[max(0, box.start - 16) : min(len(data), box.end + 16)]
    return (window or b"\x00")[:256]


def mutate(data: bytes, start: int, span: int, off: int, op: int, sample: int) -> bytes:
    boxes = parse_boxes(data)
    if not boxes:
        return data
    box = pick_box(boxes, start, span, op, sample)
    selector = op % 8
    out = bytearray(data)

    if selector == 0 and box.header == 8:
        deltas = [-8, -1, 1, 8, 16, 32]
        delta = deltas[sample % len(deltas)]
        new_size = clamp(box.size + delta, box.header, len(data) - box.start)
        put_u32(out, box.start, new_size)
    elif selector == 1:
        chunk = data[box.start : box.end]
        out = bytearray(data[: box.end] + chunk + data[box.end :])
    elif selector == 2 and len(boxes) > 1:
        delete_box = box if box.box_type != b"ftyp" else next(
            (item for item in boxes if item.box_type != b"ftyp"),
            box,
        )
        if delete_box.box_type != b"ftyp":
            out = bytearray(data[: delete_box.start] + data[delete_box.end :])
        else:
            out = bytearray(data + make_box(b"free", bytes([sample & 0xFF]) * 4))
    elif selector == 3:
        filler_len = 8 + 4 * (1 + sample % 8)
        filler = make_box(b"free", bytes([sample & 0xFF]) * (filler_len - 8))
        out = bytearray(data[: box.start] + filler + data[box.start :])
    elif selector == 4:
        replacement = KNOWN_BOX_TYPES[(sample + len(boxes)) % len(KNOWN_BOX_TYPES)]
        out[box.start + 4 : box.start + 8] = replacement
    elif selector == 5 and box.header == 8:
        payload = useful_payload(data, box, off, sample)
        insert_at = clamp(off, box.start + box.header, box.end)
        out = bytearray(data[:insert_at] + payload[: 1 + sample % 16] + data[insert_at:])
        put_u32(out, box.start, box.size + 1 + sample % 16)
    elif selector == 6 and box.header == 8:
        payload_start = box.start + box.header
        payload_end = box.end
        if payload_start < payload_end:
            delete_len = clamp(1 + sample % 16, 1, payload_end - payload_start)
            delete_at = clamp(off, payload_start, payload_end - delete_len)
            out = bytearray(data[:delete_at] + data[delete_at + delete_len :])
            put_u32(out, box.start, box.size - delete_len)
    else:
        payload = useful_payload(data, box, off, sample)
        appended = make_box(KNOWN_BOX_TYPES[(op + sample) % len(KNOWN_BOX_TYPES)], payload)
        out = bytearray(data + appended)

    result = bytes(out[:MAX_OUTPUT_LEN]) or data
    if result == data:
        fallback = make_box(KNOWN_BOX_TYPES[(op + sample) % len(KNOWN_BOX_TYPES)], b"\x00")
        result = bytes((bytearray(data) + fallback)[:MAX_OUTPUT_LEN])
    return result


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

    source = mutated if parse_boxes(mutated) else original
    repaired = mutate(source, start, span, off, op, sample)
    if repaired == original:
        repaired = mutated

    with open(out_path, "wb") as handle:
        handle.write(repaired[:MAX_OUTPUT_LEN])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
