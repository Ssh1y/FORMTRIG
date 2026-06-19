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
LAYER_STRESS_IDS = [0, 1, 2, 4, 7, 14, 22, 31, 36, 46, 50]
LAYERED_TRAIN_TYPES = [32, 33, 34, 32, 33, 34, 14, 16, 21, 49]
VPS_MAX_LAYERS_MINUS1 = [0, 1, 2, 3, 4, 15, 46, 63]
VPS_MAX_LAYER_ID = [0, 1, 2, 3, 4, 7, 22, 31, 50, 63]


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


def set_bits(payload: bytes, bit_offset: int, bit_len: int, value: int) -> bytes:
    out = bytearray(payload)
    needed = (bit_offset + bit_len + 7) // 8
    if len(out) < needed:
        out.extend(b"\x80" * (needed - len(out)))
    for index in range(bit_len):
        bit = (value >> (bit_len - 1 - index)) & 1
        absolute = bit_offset + index
        byte_index = absolute // 8
        shift = 7 - (absolute % 8)
        if bit:
            out[byte_index] |= 1 << shift
        else:
            out[byte_index] &= ~(1 << shift)
    return bytes(out)


def get_bits(payload: bytes, bit_offset: int, bit_len: int) -> int:
    value = 0
    for index in range(bit_len):
        absolute = bit_offset + index
        byte_index = absolute // 8
        shift = 7 - (absolute % 8)
        bit = 0
        if byte_index < len(payload):
            bit = (payload[byte_index] >> shift) & 1
        value = (value << 1) | bit
    return value


def nalus_of_type(data: bytes, nalus: list[Nalu], nal_type: int) -> list[Nalu]:
    return [nalu for nalu in nalus if nalu_type(data, nalu) == nal_type]


def nalu_body(data: bytes, nalu: Nalu) -> bytes:
    body_start = min(nalu.payload_start + 2, nalu.end)
    return data[body_start:nalu.end]


def payload_for_type(data: bytes, nalus: list[Nalu], nal_type: int, fallback: Nalu, sample: int) -> bytes:
    typed = nalus_of_type(data, nalus, nal_type)
    source = typed[sample % len(typed)] if typed else fallback
    payload = nalu_body(data, source) or b"\x80"
    if nal_type == 49:
        return extractor_payload(sample)
    if nal_type in (14, 16, 21):
        return stress_payload(payload, sample, min_len=24)
    if nal_type in (32, 33, 34):
        return stress_payload(payload, sample, min_len=40)
    return stress_payload(payload, sample, min_len=16)


def stress_payload(payload: bytes, sample: int, min_len: int) -> bytes:
    if not payload:
        payload = b"\x80"
    repeat = (min_len + len(payload) - 1) // len(payload)
    out = bytearray((payload * max(1, repeat))[: max(min_len, min(len(payload), 128))])
    for index in range(min(8, len(out))):
        out[index] ^= (0x21 + sample * 17 + index * 29) & 0xFF
    if out:
        out[-1] |= 0x80
    return bytes(out)


def vps_field_payload(base_payload: bytes, sample: int) -> bytes:
    payload = stress_payload(base_payload, sample, min_len=96)
    max_layers_minus1 = VPS_MAX_LAYERS_MINUS1[(sample // 2) % len(VPS_MAX_LAYERS_MINUS1)]
    max_sub_layers_minus1 = (sample // 3) % 7
    payload = set_bits(payload, 0, 4, sample & 0x0F)
    payload = set_bits(payload, 4, 1, 1)
    payload = set_bits(payload, 5, 1, 1)
    payload = set_bits(payload, 6, 6, max_layers_minus1)
    payload = set_bits(payload, 12, 3, max_sub_layers_minus1)
    payload = set_bits(payload, 15, 1, 1)
    payload = set_bits(payload, 16, 16, 0xFFFF)
    tail = bytearray(payload)
    if len(tail) < 80:
        tail.extend(b"\x80" * (80 - len(tail)))
    tail[48 + (sample % 16)] ^= VPS_MAX_LAYER_ID[sample % len(VPS_MAX_LAYER_ID)]
    tail[-1] = (tail[-1] & 0xFE) | ((sample >> 1) & 1)
    return bytes(tail)


def sps_field_payload(base_payload: bytes, sample: int) -> bytes:
    payload = set_bits(stress_payload(base_payload, sample, min_len=96), 0, 4, sample & 0x0F)
    payload = set_bits(payload, 4, 3, (sample // 2) % 7)
    payload = set_bits(payload, 7, 1, 1)
    tail = bytearray(payload)
    for index in range(min(12, len(tail))):
        tail[index] ^= (0x5A + sample * 13 + index * 7) & 0xFF
    tail[-1] |= 0x80
    return bytes(tail)


def pps_field_payload(base_payload: bytes, sample: int) -> bytes:
    tail = bytearray(stress_payload(base_payload, sample, min_len=64))
    for index in range(min(10, len(tail))):
        tail[index] ^= (0x33 + sample * 19 + index * 11) & 0xFF
    tail[-1] |= 0x80
    return bytes(tail)


def parameter_payload(data: bytes, nalus: list[Nalu], nal_type: int, fallback: Nalu, sample: int) -> bytes:
    base = payload_for_type(data, nalus, nal_type, fallback, sample)
    if nal_type == 32:
        return vps_field_payload(base, sample)
    if nal_type == 33:
        return sps_field_payload(base, sample)
    if nal_type == 34:
        return pps_field_payload(base, sample)
    return base


def field_parameter_train(data: bytes, nalus: list[Nalu], anchor: Nalu, sample: int) -> bytes:
    chunks = []
    for index, nal_type in enumerate((32, 33, 34, 32, 33, 34)):
        layer = LAYER_STRESS_IDS[(sample + index) % len(LAYER_STRESS_IDS)]
        payload = parameter_payload(data, nalus, nal_type, anchor, sample + index)
        chunks.append(make_nalu(nal_type, payload, layer))
    return b"".join(chunks)


def extractor_payload(sample: int) -> bytes:
    pattern = bytes(
        [
            0x00,
            0x01 + (sample & 0x03),
            0x00,
            0x00,
            0x00,
            0x01,
            0x40 | (sample & 0x3F),
            0x95,
            0x82,
            0x40,
            0x00,
            0x80,
        ]
    )
    return pattern


def layered_parameter_train(data: bytes, nalus: list[Nalu], anchor: Nalu, sample: int) -> bytes:
    chunks = []
    for index, nal_type in enumerate(LAYERED_TRAIN_TYPES):
        layer = LAYER_STRESS_IDS[(sample + index) % len(LAYER_STRESS_IDS)]
        payload = payload_for_type(data, nalus, nal_type, anchor, sample + index)
        chunks.append(make_nalu(nal_type, payload, layer))
    return b"".join(chunks)


def first_slice_or_anchor(data: bytes, nalus: list[Nalu], anchor: Nalu) -> Nalu:
    for nalu in nalus:
        if nalu_type(data, nalu) in (0, 1, 14, 16, 19, 20, 21):
            return nalu
    return anchor


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
    selector = op % 20
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
    elif selector == 7:
        payload = payload_window(data, nalu, off, sample)
        prefix = make_nalu(32, payload[:48], 0)
        prefix += make_nalu(33, payload[8:72], 1)
        prefix += make_nalu(34, payload[16:80], 1)
        prefix += make_nalu(19, payload[24:96], 1)
        out = prefix + data
    elif selector == 8:
        anchor = first_slice_or_anchor(data, nalus, nalu)
        train = layered_parameter_train(data, nalus, anchor, sample)
        out = data[: anchor.start] + train + data[anchor.start :]
    elif selector == 9:
        anchor = first_slice_or_anchor(data, nalus, nalu)
        burst = []
        for index, nal_type in enumerate((14, 16, 21, 0, 1, 16, 14)):
            layer = LAYER_STRESS_IDS[(sample + index * 2) % len(LAYER_STRESS_IDS)]
            payload = payload_for_type(data, nalus, nal_type, anchor, sample + index)
            burst.append(make_nalu(nal_type, payload, layer))
        out = data[: anchor.start] + b"".join(burst) + data[anchor.start :]
    elif selector == 10:
        out_buf = bytearray(data)
        type_cycle = (32, 33, 34, 14, 16, 21, 49)
        for index, item in enumerate(nalus):
            if item.payload_start + 2 > item.end:
                continue
            if index % 2 != sample % 2:
                continue
            nal_type = type_cycle[(sample + index) % len(type_cycle)]
            layer = LAYER_STRESS_IDS[(sample + index) % len(LAYER_STRESS_IDS)]
            tid = out_buf[item.payload_start + 1] & 0x07
            out_buf[item.payload_start : item.payload_start + 2] = make_header(nal_type, layer, tid or 1)
        out = bytes(out_buf)
    elif selector == 11:
        anchor = first_slice_or_anchor(data, nalus, nalu)
        train = layered_parameter_train(data, nalus, anchor, sample)
        payload = payload_window(data, anchor, off, sample)
        layer = LAYER_STRESS_IDS[(sample + 5) % len(LAYER_STRESS_IDS)]
        extractor = make_nalu(49, extractor_payload(sample), layer)
        out = train + extractor + make_nalu(20, stress_payload(payload, sample, 64), layer) + data
    elif selector == 12:
        anchor = first_slice_or_anchor(data, nalus, nalu)
        payload = payload_window(data, anchor, off, sample)
        inflated = b"".join(
            make_nalu(20 if index % 2 else 16, stress_payload(payload, sample + index, 96), LAYER_STRESS_IDS[(sample + index) % len(LAYER_STRESS_IDS)])
            for index in range(4)
        )
        out = data[: anchor.end] + inflated + data[anchor.end :]
    elif selector == 13:
        anchor = first_slice_or_anchor(data, nalus, nalu)
        repetitions = 2 + (sample % 4)
        out = data
        insert_at = anchor.start
        for index in range(repetitions):
            train = layered_parameter_train(data, nalus, anchor, sample + index)
            out = out[:insert_at] + train + out[insert_at:]
            insert_at += len(train)
    elif selector == 14:
        anchor = first_slice_or_anchor(data, nalus, nalu)
        train = field_parameter_train(data, nalus, anchor, sample)
        out = data[: anchor.start] + train + data[anchor.start :]
    elif selector == 15:
        out_buf = bytearray(data)
        for item in nalus:
            nal_type = nalu_type(data, item)
            if nal_type not in (32, 33, 34):
                continue
            payload = parameter_payload(data, nalus, nal_type, item, sample + item.start)
            replace_len = max(0, item.end - item.payload_start - 2)
            out_buf[item.payload_start + 2 : item.end] = payload[:replace_len]
        out = bytes(out_buf)
    elif selector == 16:
        anchor = first_slice_or_anchor(data, nalus, nalu)
        train = field_parameter_train(data, nalus, anchor, sample)
        payload = payload_window(data, anchor, off, sample)
        layer = VPS_MAX_LAYER_ID[sample % len(VPS_MAX_LAYER_ID)]
        out = train + make_nalu(49, extractor_payload(sample), layer) + make_nalu(20, stress_payload(payload, sample, 96), layer) + data
    elif selector == 17:
        anchor = first_slice_or_anchor(data, nalus, nalu)
        chunks = []
        for index in range(2 + (sample % 3)):
            chunks.append(field_parameter_train(data, nalus, anchor, sample + index))
            payload = stress_payload(payload_window(data, anchor, off, sample + index), sample + index, 48)
            layer = VPS_MAX_LAYER_ID[(sample + index) % len(VPS_MAX_LAYER_ID)]
            chunks.append(make_nalu(16 if index % 2 else 14, payload, layer))
        out = b"".join(chunks) + data
    elif selector == 18:
        vps_items = nalus_of_type(data, nalus, 32)
        target = vps_items[sample % len(vps_items)] if vps_items else nalu
        payload = vps_field_payload(nalu_body(data, target), sample)
        layer = VPS_MAX_LAYER_ID[(sample // 2) % len(VPS_MAX_LAYER_ID)]
        out = data[: target.start] + make_nalu(32, payload, layer) + data[target.end :]
    else:
        anchor = first_slice_or_anchor(data, nalus, nalu)
        train = field_parameter_train(data, nalus, anchor, sample)
        payload = stress_payload(payload_window(data, anchor, off, sample), sample, 128)
        layer_a = VPS_MAX_LAYER_ID[sample % len(VPS_MAX_LAYER_ID)]
        layer_b = VPS_MAX_LAYER_ID[(sample + 3) % len(VPS_MAX_LAYER_ID)]
        out = train + make_nalu(0, payload, layer_a) + make_nalu(1, payload[::-1], layer_b) + data

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
