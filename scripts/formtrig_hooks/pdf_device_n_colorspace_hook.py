#!/usr/bin/env python3
"""FORMTRIG typed-mutation hook for PDF image color-space structure.

The hook is format-level, not oracle-level: it tries plausible PDF image
dictionary rewrites that increase color-component diversity. One candidate is
a high-component DeviceN color space, which keeps Poppler's secondary
color-space pointer unset while making image component count larger.
"""

from __future__ import annotations

import re
import sys


MAX_OUTPUT_LEN = 1 << 20
COLORSPACE_RE = re.compile(rb"/ColorSpace\s+(?:/\w+|\[[^\]]{0,512}\])")
BITS_RE = re.compile(rb"/BitsPerComponent\s+\d+")
IMAGE_DICT_RE = re.compile(
    rb"<<(?=[^<>]{0,1024}/Subtype\s*/Image\b)(?P<body>[^<>]{0,4096})>>",
    re.DOTALL,
)
OBJECT_RE = re.compile(rb"(?ms)^(\d+)\s+0\s+obj\b.*?^endobj\s*")


def clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(value, hi))


def device_n_space(ncomps: int) -> bytes:
    names = b" ".join(f"/FT{i}".encode("ascii") for i in range(1, ncomps + 1))
    return b"[/DeviceN [" + names + b"] /DeviceRGB /Identity]"


def build_pdf(objects: list[bytes]) -> bytes:
    out = bytearray(b"%PDF-1.4\n%\xff\xff\xff\xff\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(out))
        out.extend(obj)
        if not out.endswith(b"\n"):
            out.extend(b"\n")

    xref_offset = len(out)
    out.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    out.extend(b"trailer\n")
    out.extend(f"<< /Size {len(offsets)} /Root 1 0 R >>\n".encode("ascii"))
    out.extend(b"startxref\n")
    out.extend(f"{xref_offset}\n%%EOF\n".encode("ascii"))
    return bytes(out)


def minimal_image_pdf(selector: int) -> bytes:
    variants = [
        (b"/DeviceRGB", b"\xff\x00\x00", b"8"),
        (b"/DeviceRGB", b"\x00\xff\x00", b"8"),
        (b"/DeviceCMYK", b"\x00\xff\xff\x00", b"8"),
        (device_n_space(3), b"\x00\x80\xff", b"8"),
        (b"/DeviceGray", b"\x7f", b"8"),
    ]
    color_space, pixel, bits = variants[selector % len(variants)]
    image_dict = (
        b"<< /Type /XObject /Subtype /Image /Width 1 /Height 1 "
        b"/ColorSpace "
        + color_space
        + b" /BitsPerComponent "
        + bits
        + b" /Length "
        + str(len(pixel)).encode("ascii")
        + b" >>"
    )
    content = b"q 1 0 0 1 0 0 cm /Im0 Do Q\n"
    return build_pdf(
        [
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
            b"3 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] "
            b"/Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>\n"
            b"endobj\n",
            b"4 0 obj\n"
            + image_dict
            + b"\nstream\n"
            + pixel
            + b"\nendstream\nendobj\n",
            b"5 0 obj\n<< /Length "
            + str(len(content)).encode("ascii")
            + b" >>\nstream\n"
            + content
            + b"endstream\nendobj\n",
        ]
    )


def replace_or_insert(body: bytes, key_re: re.Pattern[bytes], key: bytes, value: bytes) -> bytes:
    replacement = key + b" " + value
    if key_re.search(body):
        return key_re.sub(replacement, body, count=1)
    return body.rstrip() + b"\n" + replacement + b"\n"


def strip_filter(body: bytes) -> bytes:
    return re.sub(rb"\s*/Filter\s+(?:/\w+|\[[^\]]{0,256}\])", b"", body, count=1)


def mutate_image_dict(body: bytes, selector: int) -> bytes:
    ncomps = 9 + (selector % 4)
    out = replace_or_insert(body, COLORSPACE_RE, b"/ColorSpace", device_n_space(ncomps))

    if selector % 5 in (1, 3):
        out = replace_or_insert(out, BITS_RE, b"/BitsPerComponent", b"1")
    elif selector % 5 == 2:
        out = replace_or_insert(out, BITS_RE, b"/BitsPerComponent", b"8")

    if selector % 7 == 4:
        out = strip_filter(out)

    return out


def mutate_first_image(data: bytes, selector: int) -> bytes | None:
    matches = list(IMAGE_DICT_RE.finditer(data))
    if not matches:
        return None

    match = matches[selector % len(matches)]
    body = match.group("body")
    new_body = mutate_image_dict(body, selector)
    if new_body == body:
        return None
    return data[: match.start("body")] + new_body + data[match.end("body") :]


def mutate_colorspace_entry(data: bytes, selector: int) -> bytes | None:
    matches = list(COLORSPACE_RE.finditer(data))
    if not matches:
        return None

    match = matches[selector % len(matches)]
    replacement = b"/ColorSpace " + device_n_space(9 + (selector % 4))
    return data[: match.start()] + replacement + data[match.end() :]


def insert_pdf_literal(data: bytes, off: int, op: int, sample: int) -> bytes:
    snippets = [
        b"/ColorSpace " + device_n_space(9) + b"\n",
        b"/BitsPerComponent 1\n/ColorSpace " + device_n_space(10) + b"\n",
        b"/Decode [0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1]\n",
    ]
    snippet = snippets[(op + sample) % len(snippets)]
    off = clamp(off, 0, len(data))
    return data[:off] + snippet + data[off:]


def mutate(data: bytes, fallback: bytes, off: int, op: int, sample: int) -> bytes:
    if not data.startswith(b"%PDF"):
        return fallback

    selector = op + sample * 17
    if selector % 3 != 2:
        return minimal_image_pdf(selector)[:MAX_OUTPUT_LEN]

    out = mutate_colorspace_entry(data, selector)
    if out is None:
        out = mutate_first_image(data, selector)
    if out is None:
        out = insert_pdf_literal(data, off, op, sample)
    if out == data:
        out = fallback
    rebuilt = rebuild_classic_xref(out)
    return rebuilt[:MAX_OUTPUT_LEN]


def rebuild_classic_xref(data: bytes) -> bytes:
    matches = list(OBJECT_RE.finditer(data))
    if not matches:
        return data

    first_obj = matches[0].start()
    header = data[:first_obj]
    if not header.startswith(b"%PDF"):
        header = b"%PDF-1.4\n%\xff\xff\xff\xff\n"
    elif not header.endswith(b"\n"):
        header += b"\n"

    out = bytearray(header)
    offsets: dict[int, int] = {}
    max_obj = 0
    for match in matches:
        obj_num = int(match.group(1))
        max_obj = max(max_obj, obj_num)
        if out and not out.endswith(b"\n"):
            out.extend(b"\n")
        offsets[obj_num] = len(out)
        out.extend(match.group(0).rstrip())
        out.extend(b"\n")

    xref_offset = len(out)
    size = max_obj + 1
    out.extend(f"xref\n0 {size}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for obj_num in range(1, size):
        offset = offsets.get(obj_num)
        if offset is None:
            out.extend(b"0000000000 65535 f \n")
        else:
            out.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

    root = 1 if 1 in offsets else min(offsets)
    out.extend(b"trailer\n")
    out.extend(f"<< /Size {size}\n/Root {root} 0 R >>\n".encode("ascii"))
    out.extend(b"startxref\n")
    out.extend(f"{xref_offset}\n%%EOF\n".encode("ascii"))
    return bytes(out)


def main(argv: list[str]) -> int:
    if len(argv) < 15:
        return 2
    orig_path, mut_path, out_path = argv[1], argv[2], argv[3]
    off = int(argv[7])
    op = int(argv[8])
    sample = int(argv[9])

    with open(orig_path, "rb") as handle:
        original = handle.read()
    with open(mut_path, "rb") as handle:
        mutated = handle.read()

    out = mutate(original, mutated, off, op, sample)
    with open(out_path, "wb") as handle:
        handle.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
