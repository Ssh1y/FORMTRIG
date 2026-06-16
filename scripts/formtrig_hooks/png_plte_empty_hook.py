#!/usr/bin/env python3
import os
import struct
import sys
import zlib


PNG_SIG = b"\x89PNG\r\n\x1a\n"


def png_chunk(chunk_type, payload):
    crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + chunk_type + payload + struct.pack(">I", crc)


def replace_plte_with_empty(data, start, span):
    if not data.startswith(PNG_SIG):
        return None
    if start + 12 > len(data):
        return None
    length = int.from_bytes(data[start : start + 4], "big")
    chunk_type = data[start + 4 : start + 8]
    total = 12 + length
    if chunk_type != b"PLTE" or start + total > len(data):
        return None
    if span and span < total:
        return None
    return data[:start] + png_chunk(b"PLTE", b"") + data[start + total :]


def main(argv):
    if len(argv) < 15:
        return 2
    orig_path, mut_path, out_path = argv[1], argv[2], argv[3]
    start = int(argv[5])
    span = int(argv[6])

    with open(orig_path, "rb") as f:
        orig = f.read()
    with open(mut_path, "rb") as f:
        mutated = f.read()

    repaired = replace_plte_with_empty(orig, start, span)
    if repaired is None:
        repaired = mutated

    with open(out_path, "wb") as f:
        f.write(repaired)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
