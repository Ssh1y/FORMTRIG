#!/usr/bin/env python3
import sys


MAX_NAME_LEN = 100
MAX_OUTPUT_LEN = 4096


def parse_entries(data):
    entries = []
    if len(data) < 3:
        return entries
    pos = 2
    remaining = len(data) - 2
    while remaining > 10 and pos < len(data):
        name_len = (data[pos] % 100) + 1
        if name_len > remaining - 1:
            name_len = remaining - 1
        name_start = pos + 1
        name_end = name_start + name_len
        name = data[name_start:name_end]
        pos = name_end
        remaining -= name_len + 1
        if remaining < 2 or pos + 2 > len(data):
            break
        content_len = (data[pos] | (data[pos + 1] << 8)) % 1024
        if content_len > remaining - 2:
            content_len = remaining - 2
        pos += 2 + content_len
        remaining -= 2 + content_len
        entries.append(name)
    return entries


def safe_segment(segment, fallback):
    out = bytearray()
    for byte in segment:
        if 48 <= byte <= 57 or 65 <= byte <= 90 or 97 <= byte <= 122:
            out.append(byte)
        elif byte in (45, 95):
            out.append(byte)
    if not out or out in (b".", b".."):
        return fallback
    return bytes(out[:16])


def seed_segments(data):
    for name in parse_entries(data):
        parts = [p for p in name.split(b"/") if p and p not in (b".", b"..")]
        if len(parts) >= 2:
            dirs = parts[:-1] if len(parts) > 2 else parts
            cleaned = [
                safe_segment(part, ("d%d" % idx).encode("ascii"))
                for idx, part in enumerate(dirs)
            ]
            if cleaned:
                return cleaned
    return [b"a", b"b", b"c"]


def entry(name, payload=b""):
    name = name[:MAX_NAME_LEN]
    payload = payload[:1023]
    return (
        bytes([(len(name) - 1) % 100])
        + name
        + (len(payload) % 1024).to_bytes(2, "little")
        + payload
    )


def repeat_to_depth(parts, depth):
    if not parts:
        parts = [b"a", b"b", b"c"]
    return [parts[i % len(parts)] for i in range(depth)]


def deep_path(parts, depth, basename):
    dirs = repeat_to_depth(parts, depth)
    name = b"/".join(dirs + [basename])
    while len(name) > MAX_NAME_LEN and depth > 1:
        depth -= 1
        dirs = repeat_to_depth(parts, depth)
        name = b"/".join(dirs + [basename])
    return name[:MAX_NAME_LEN]


def build_candidate(orig, mutated, op, sample):
    source = mutated if len(mutated) >= 3 else orig
    parts = seed_segments(source) or seed_segments(orig)
    selector = (op + sample * 7) % 8
    depths = [8, 10, 12, 14, 16, 18, 20, 22]
    depth = depths[selector]
    basename = b"file.txt"

    out = bytearray()
    out += b"\x04\x03"

    if selector % 4 == 0:
        out += entry(deep_path(parts, depth, basename))
    elif selector % 4 == 1:
        parent = repeat_to_depth(parts, depth)
        out += entry(b"/".join(parent + [b"one.txt"])[:MAX_NAME_LEN])
        out += entry(b"/".join(parent + [b"two.txt"])[:MAX_NAME_LEN])
    elif selector % 4 == 2:
        dotlike = []
        for idx in range(depth):
            base = parts[idx % len(parts)]
            if idx % 2 == 0:
                dotlike.append((base + b"..")[:16])
            else:
                dotlike.append(base)
        out += entry(b"/".join(dotlike + [basename])[:MAX_NAME_LEN])
    else:
        out += entry(deep_path(parts, depth, basename))
        sibling = parts + [b"sibling"]
        out += entry(deep_path(sibling, max(4, depth - 2), b"alt.txt"))

    out += b"\x00" * 8
    return bytes(out[:MAX_OUTPUT_LEN])


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

    repaired = build_candidate(orig, mutated, op, sample)
    if repaired == orig:
        repaired = mutated

    with open(out_path, "wb") as f:
        f.write(repaired)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
