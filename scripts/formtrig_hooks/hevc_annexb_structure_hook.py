#!/usr/bin/env python3
"""Typed FORMTRIG mutation hook for Annex-B HEVC elementary streams.

The hook is format-level rather than PoC-level. It preserves the Annex-B start
code framing used by raw HEVC inputs and mutates NAL unit type, order, and local
payload shape so GPAC's HEVC import/rewrite paths remain reachable.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass


MAX_OUTPUT_LEN = 65536
START3 = b"\x00\x00\x01"
START4 = b"\x00\x00\x00\x01"
INTERESTING_TYPES = [32, 33, 34, 35, 39, 14, 16, 19, 20, 48, 49]


@dataclass(frozen=True)
class Nalu:
    start: int
    prefix_len: int
    payload_start: int
    end: int

    @property
    def header_start(self) -> int:
        return self.start + self.prefix_len

    @property
    def payload(self) -> bytes:
        raise AttributeError("payload requires source bytes")


def find_start_codes(data: bytes) -> list[tuple[int, int]]:
    starts: list[tuple[int, int]] = []
    pos = 0
    limit = len(data)
    while pos + 3 <= limit:
        found3 = data.find(START3, pos)
        found4 = data.find(START4, pos)
        if found3 < 0 and found4 < 0:
            break
        if found4 >= 0 and (found3 < 0 or found4 <= found3):
            starts.append((found4, 4))
            pos = found4 + 4
        else:
            starts.append((found3, 3))
            pos = found3 + 3
    deduped: list[tuple[int, int]] = []
    for off, size in starts:
        if deduped and off < deduped[-1][0] + deduped[-1][1]:
            continue
        deduped.append((off, size))
    return deduped


def parse_nalus(data: bytes) -> list[Nalu]:
    starts = find_start_codes(data)
    nalus: list[Nalu] = []
    for index, (off, prefix_len) in enumerate(starts):
        next_start = starts[index + 1][0] if index + 1 < len(starts) else len(data)
        payload_start = off + prefix_len
        if payload_start + 2 <= next_start:
            nalus.append(Nalu(off, prefix_len, payload_start, next_start))
    return nalus


def clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(value, upper))


def nalu_type(data: bytes, nalu: Nalu) -> int:
    if nalu.payload_start + 2 > nalu.end:
        return -1
    return (data[nalu.payload_start] >> 1) & 0x3F


def layer_id(data: bytes, nalu: Nalu) -> int:
    if nalu.payload_start + 2 > nalu.end:
        return 0
    return ((data[nalu.payload_start] & 0x01) << 5) | (data[nalu.payload_start + 1] >> 3)


def make_header(nal_type: int, layer: int = 0, tid_plus_one: int = 1) -> bytes:
    layer &= 0x3F
    tid_plus_one = clamp(tid_plus_one, 1, 7)
    first = (((nal_type & 0x3F) << 1) & 0x7E) | ((layer >> 5) & 0x01)
    second = ((layer & 0x1F) << 3) | (tid_plus_one & 0x07)
    return bytes([first, second])


def make_nalu(nal_type: int, payload: bytes = b"\x80", layer: int = 0) -> bytes:
    payload = payload[:1024] or b"\x80"
    return START4 + make_header(nal_type, layer) + payload


def payload_window(data: bytes, nalu: Nalu, off: int, sample: int) -> bytes:
    body_start = min(nalu.payload_start + 2, nalu.end)
    if body_start >= nalu.end:
        return b"\x80"
    window_start = clamp(off, body_start, nalu.end)
    window_len = 8 + (sample % 56)
    window_end = clamp(window_start + window_len, window_start, nalu.end)
    return data[window_start:window_end] or data[body_start:nalu.end][:64] or b"\x80"


def choose_nalu(nalus: list[Nalu], start: int, span: int, off: int, op: int, sample: int) -> Nalu:
    if not nalus:
        raise ValueError("no nalus")
    end = start + max(span, 1)
    overlapping = [nalu for nalu in nalus if nalu.start < end and nalu.end > start]
    if not overlapping:
        overlapping = [nalu for nalu in nalus if nalu.start <= off < nalu.end]
    candidates = overlapping or nalus
    return candidates[(op + sample) % len(candidates)]


def replace_nalu_header(data: bytes, nalu: Nalu, nal_type: int, layer: int | None = None) -> bytes:
    out = bytearray(data)
    if nalu.payload_start + 2 <= nalu.end:
        if layer is None:
            layer = layer_id(data, nalu)
        tid = out[nalu.payload_start + 1] & 0x07
        out[nalu.payload_start : nalu.payload_start + 2] = make_header(nal_type, layer, tid or 1)
    return bytes(out)


def nalu_slice_with_header(data: bytes, nalu: Nalu, nal_type: int, layer: int) -> bytes:
    local = Nalu(0, nalu.prefix_len, nalu.prefix_len, nalu.end - nalu.start)
    return replace_nalu_header(data[nalu.start : nalu.end], local, nal_type, layer)


def mutate(data: bytes, start: int, span: int, off: int, op: int, sample: int) -> bytes:
    nalus = parse_nalus(data)
    if not nalus:
        return data
    nalu = choose_nalu(nalus, start, span, off, op, sample)
    selector = op % 8
    out = data

    if selector == 0:
        nal_type = INTERESTING_TYPES[sample % len(INTERESTING_TYPES)]
        layer = (sample // len(INTERESTING_TYPES)) % 4
        out = replace_nalu_header(data, nalu, nal_type, layer)
    elif selector == 1:
        out = data[: nalu.end] + data[nalu.start : nalu.end] + data[nalu.end :]
    elif selector == 2:
        payload = payload_window(data, nalu, off, sample)
        nal_type = INTERESTING_TYPES[(op + sample) % len(INTERESTING_TYPES)]
        layer = 1 + (sample % 3)
        out = data[: nalu.start] + make_nalu(nal_type, payload, layer) + data[nalu.start :]
    elif selector == 3:
        cut = clamp(off, nalu.payload_start + 2, nalu.end)
        if cut < nalu.end:
            out = data[:cut] + START4 + data[cut:]
    elif selector == 4:
        keep = clamp(2 + (sample % 32), 2, max(2, nalu.end - nalu.payload_start))
        out = data[: nalu.payload_start + keep] + data[nalu.end :]
    elif selector == 5:
        payload = payload_window(data, nalu, off, sample)
        insert_at = clamp(off, nalu.payload_start + 2, nalu.end)
        out = data[:insert_at] + payload + data[insert_at:]
    elif selector == 6 and len(nalus) > 1:
        partner = nalus[(sample + 1) % len(nalus)]
        replacement = nalu_slice_with_header(
            data,
            partner,
            nalu_type(data, partner),
            1 + (sample % 3),
        )
        out = data[: nalu.start] + replacement + data[nalu.end :]
    else:
        payload = payload_window(data, nalu, off, sample)
        prefix = make_nalu(32, payload[:48], 0)
        prefix += make_nalu(33, payload[8:72], 1)
        prefix += make_nalu(34, payload[16:80], 1)
        prefix += make_nalu(19, payload[24:96], 1)
        out = prefix + data

    out = out[:MAX_OUTPUT_LEN]
    return out if out and out != data else (data + make_nalu(INTERESTING_TYPES[sample % len(INTERESTING_TYPES)], layer=1))[:MAX_OUTPUT_LEN]


def source_bytes(original: bytes, mutated: bytes) -> bytes:
    if parse_nalus(mutated):
        return mutated
    if parse_nalus(original):
        return original
    return mutated or original


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

    source = source_bytes(original, mutated)
    repaired = mutate(source, start, span, off, op, sample)
    if repaired == original:
        repaired = mutated

    with open(out_path, "wb") as handle:
        handle.write(repaired[:MAX_OUTPUT_LEN])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
