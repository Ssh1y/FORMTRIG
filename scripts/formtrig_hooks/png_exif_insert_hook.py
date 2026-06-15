#!/usr/bin/env python3
import struct
import sys
import zlib


PNG_SIG = b"\x89PNG\r\n\x1a\n"


def png_chunk(chunk_type, payload, crc_override=None):
    crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
    if crc_override is not None:
        crc = crc_override & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + chunk_type + payload + struct.pack(">I", crc)


def chunk_bounds(data):
    if not data.startswith(PNG_SIG):
        return
    pos = len(PNG_SIG)
    while pos + 12 <= len(data):
        length = int.from_bytes(data[pos : pos + 4], "big")
        chunk_type = data[pos + 4 : pos + 8]
        end = pos + 12 + length
        if end > len(data):
            return
        yield pos, end, chunk_type, length
        pos = end
        if chunk_type == b"IEND":
            return


def insert_exif_after_ihdr(data, op, sample):
    insert_at = None
    for start, end, chunk_type, _ in chunk_bounds(data) or ():
        if chunk_type == b"eXIf":
            return None
        if chunk_type == b"IHDR":
            insert_at = end
            break
    if insert_at is None:
        return None

    selector = (op + sample) % 3
    if selector == 0:
        exif = png_chunk(b"eXIf", b"MM")
    elif selector == 1:
        exif = png_chunk(b"eXIf", b"II\x00\x00\x00\x08")
    else:
        payload = b"MM\x00\x00\x00\x08"
        exif = png_chunk(b"eXIf", payload, crc_override=0)

    return data[:insert_at] + exif + data[insert_at:]


def main(argv):
    if len(argv) < 15:
        return 2
    orig_path, mut_path, out_path = argv[1], argv[2], argv[3]
    op = int(argv[8])
    sample = int(argv[9])

    with open(orig_path, "rb") as f:
        orig = f.read()
    with open(mut_path, "rb") as f:
        mutated = f.read()

    repaired = insert_exif_after_ihdr(orig, op, sample)
    if repaired is None:
        repaired = mutated

    with open(out_path, "wb") as f:
        f.write(repaired)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
