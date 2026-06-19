#!/usr/bin/env python3
"""Audit GPAC_3403 HEVC structure gaps between PoC, seeds, and variants.

This diagnostic is intentionally separate from the mutator.  It measures
Annex-B NAL-unit structure, ISO-BMFF boxes, and replay-record variant structure
so GPAC_3403 RNT-but-not-T failures can be explained without reading harness
logic or baking PoC bytes into the fuzzer.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import string
import sys
from collections import Counter
from pathlib import Path
from types import ModuleType
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOOK = REPO_ROOT / "scripts" / "formtrig_hooks" / "hevc_annexb_structure_hook.py"
CONTAINER_BOXES = {
    "moov",
    "trak",
    "mdia",
    "minf",
    "stbl",
    "edts",
    "dinf",
    "udta",
    "mvex",
    "moof",
    "traf",
    "mfra",
}
MAX_SEQUENCE_ITEMS = 64
VCL_NAL_TYPES = set(range(0, 32))
IRAP_NAL_TYPES = set(range(16, 24))


class BitstreamError(ValueError):
    pass


class BitReader:
    def __init__(self, data: bytes):
        self.data = data
        self.bitpos = 0

    @property
    def remaining(self) -> int:
        return len(self.data) * 8 - self.bitpos

    def read_bits(self, count: int) -> int:
        if count < 0:
            raise BitstreamError("negative bit count")
        if self.remaining < count:
            raise BitstreamError("not enough bits")
        value = 0
        for _ in range(count):
            byte_index = self.bitpos // 8
            shift = 7 - (self.bitpos % 8)
            value = (value << 1) | ((self.data[byte_index] >> shift) & 1)
            self.bitpos += 1
        return value

    def read_bool(self) -> bool:
        return bool(self.read_bits(1))

    def skip_bits(self, count: int) -> None:
        self.read_bits(count)

    def read_ue(self) -> int:
        leading_zero_bits = 0
        while self.remaining:
            if self.read_bits(1):
                break
            leading_zero_bits += 1
            if leading_zero_bits > 31:
                raise BitstreamError("exp-golomb prefix too long")
        else:
            raise BitstreamError("unterminated exp-golomb code")
        suffix = self.read_bits(leading_zero_bits) if leading_zero_bits else 0
        return (1 << leading_zero_bits) - 1 + suffix


def rbsp_from_ebsp(data: bytes) -> bytes:
    out = bytearray()
    index = 0
    while index < len(data):
        if index + 2 < len(data) and data[index] == 0 and data[index + 1] == 0 and data[index + 2] == 3:
            out.extend(data[index : index + 2])
            index += 3
            continue
        out.append(data[index])
        index += 1
    return bytes(out)


def skip_profile_tier_level(reader: BitReader, max_sub_layers_minus1: int) -> None:
    reader.skip_bits(2 + 1 + 5 + 32 + 48 + 8)
    sub_layer_profile_present = []
    sub_layer_level_present = []
    for _ in range(max_sub_layers_minus1):
        sub_layer_profile_present.append(reader.read_bool())
        sub_layer_level_present.append(reader.read_bool())
    if max_sub_layers_minus1:
        for _ in range(max_sub_layers_minus1, 8):
            reader.skip_bits(2)
    for index in range(max_sub_layers_minus1):
        if sub_layer_profile_present[index]:
            reader.skip_bits(2 + 1 + 5 + 32 + 48)
        if sub_layer_level_present[index]:
            reader.skip_bits(8)


def parse_vps(rbsp: bytes) -> dict[str, Any]:
    reader = BitReader(rbsp)
    result: dict[str, Any] = {
        "kind": "vps",
        "vps_id": reader.read_bits(4),
        "base_layer_internal": int(reader.read_bool()),
        "base_layer_available": int(reader.read_bool()),
        "max_layers_minus1": reader.read_bits(6),
        "max_sub_layers_minus1": reader.read_bits(3),
        "temporal_id_nesting": int(reader.read_bool()),
    }
    reader.skip_bits(16)
    skip_profile_tier_level(reader, result["max_sub_layers_minus1"])
    ordering_info_present = reader.read_bool()
    result["sub_layer_ordering_info_present"] = int(ordering_info_present)
    ordering_start = 0 if ordering_info_present else result["max_sub_layers_minus1"]
    ordering_count = result["max_sub_layers_minus1"] - ordering_start + 1
    for _ in range(max(0, ordering_count)):
        reader.read_ue()
        reader.read_ue()
        reader.read_ue()
    result["max_layer_id"] = reader.read_bits(6)
    num_layer_sets_minus1 = reader.read_ue()
    result["num_layer_sets_minus1"] = num_layer_sets_minus1
    layer_set_bits = num_layer_sets_minus1 * (result["max_layer_id"] + 1)
    result["layer_id_included_bits"] = layer_set_bits
    if layer_set_bits > reader.remaining:
        result["truncated_layer_id_included_bits"] = layer_set_bits - reader.remaining
        reader.skip_bits(reader.remaining)
    else:
        reader.skip_bits(layer_set_bits)
    if reader.remaining:
        result["timing_info_present"] = int(reader.read_bool())
    return result


def parse_sps(rbsp: bytes) -> dict[str, Any]:
    reader = BitReader(rbsp)
    result: dict[str, Any] = {
        "kind": "sps",
        "vps_id": reader.read_bits(4),
        "max_sub_layers_minus1": reader.read_bits(3),
        "temporal_id_nesting": int(reader.read_bool()),
    }
    skip_profile_tier_level(reader, result["max_sub_layers_minus1"])
    result["sps_id"] = reader.read_ue()
    result["chroma_format_idc"] = reader.read_ue()
    if result["chroma_format_idc"] == 3:
        result["separate_colour_plane_flag"] = int(reader.read_bool())
    result["pic_width_in_luma_samples"] = reader.read_ue()
    result["pic_height_in_luma_samples"] = reader.read_ue()
    if reader.read_bool():
        result["conformance_window_flag"] = 1
        result["conf_win_left_offset"] = reader.read_ue()
        result["conf_win_right_offset"] = reader.read_ue()
        result["conf_win_top_offset"] = reader.read_ue()
        result["conf_win_bottom_offset"] = reader.read_ue()
    else:
        result["conformance_window_flag"] = 0
    result["bit_depth_luma_minus8"] = reader.read_ue()
    result["bit_depth_chroma_minus8"] = reader.read_ue()
    result["log2_max_pic_order_cnt_lsb_minus4"] = reader.read_ue()
    return result


def parse_pps(rbsp: bytes) -> dict[str, Any]:
    reader = BitReader(rbsp)
    return {
        "kind": "pps",
        "pps_id": reader.read_ue(),
        "sps_id": reader.read_ue(),
        "dependent_slice_segments_enabled": int(reader.read_bool()) if reader.remaining else None,
    }


def parse_slice_header(rbsp: bytes, nal_type: int) -> dict[str, Any]:
    reader = BitReader(rbsp)
    result: dict[str, Any] = {
        "kind": "slice",
        "first_slice_segment_in_pic": int(reader.read_bool()),
    }
    if nal_type in IRAP_NAL_TYPES:
        result["no_output_of_prior_pics"] = int(reader.read_bool())
    result["pps_id"] = reader.read_ue()
    return result


def parse_nalu_semantics(data: bytes, hook: ModuleType, nalu: Any) -> dict[str, Any]:
    nal_type = hook.nalu_type(data, nalu)
    rbsp = rbsp_from_ebsp(hook.nalu_body(data, nalu))
    try:
        if nal_type == 32:
            parsed = parse_vps(rbsp)
        elif nal_type == 33:
            parsed = parse_sps(rbsp)
        elif nal_type == 34:
            parsed = parse_pps(rbsp)
        elif nal_type in VCL_NAL_TYPES:
            parsed = parse_slice_header(rbsp, nal_type)
        else:
            parsed = {"kind": "other"}
        parsed["parse_error"] = None
        return parsed
    except BitstreamError as exc:
        return {"kind": "error", "parse_error": str(exc)}


def semantic_cross_references(items: list[dict[str, Any]]) -> dict[str, Any]:
    vps_ids = sorted({item["vps_id"] for item in items if item.get("kind") == "vps" and "vps_id" in item})
    sps_ids = sorted({item["sps_id"] for item in items if item.get("kind") == "sps" and "sps_id" in item})
    pps_ids = sorted({item["pps_id"] for item in items if item.get("kind") == "pps" and "pps_id" in item})
    sps_refs = [
        {"index": item["index"], "sps_id": item.get("sps_id"), "vps_id": item.get("vps_id")}
        for item in items
        if item.get("kind") == "sps"
    ]
    pps_refs = [
        {"index": item["index"], "pps_id": item.get("pps_id"), "sps_id": item.get("sps_id")}
        for item in items
        if item.get("kind") == "pps"
    ]
    slice_refs = [
        {"index": item["index"], "nal_type": item.get("nal_type"), "layer": item.get("layer"), "pps_id": item.get("pps_id")}
        for item in items
        if item.get("kind") == "slice"
    ]
    return {
        "vps_ids": vps_ids,
        "sps_ids": sps_ids,
        "pps_ids": pps_ids,
        "sps_refs": sps_refs[:64],
        "pps_refs": pps_refs[:64],
        "slice_refs": slice_refs[:64],
        "sps_without_vps": [ref for ref in sps_refs if ref.get("vps_id") not in vps_ids],
        "pps_without_sps": [ref for ref in pps_refs if ref.get("sps_id") not in sps_ids],
        "slice_without_pps": [ref for ref in slice_refs if ref.get("pps_id") not in pps_ids],
        "sps_without_vps_count": sum(1 for ref in sps_refs if ref.get("vps_id") not in vps_ids),
        "pps_without_sps_count": sum(1 for ref in pps_refs if ref.get("sps_id") not in sps_ids),
        "slice_without_pps_count": sum(1 for ref in slice_refs if ref.get("pps_id") not in pps_ids),
    }


def load_hook(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("formtrig_hevc_structure_hook", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load HEVC hook: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_box_type(raw: bytes) -> bool:
    text = raw.decode("latin-1", errors="ignore")
    return len(text) == 4 and all(ch in string.printable and ch not in "\r\n\t\x0b\x0c" for ch in text)


def read_box_size(data: bytes, offset: int, limit: int) -> tuple[int, int] | None:
    if offset + 8 > limit:
        return None
    size32 = int.from_bytes(data[offset : offset + 4], "big")
    box_type = data[offset + 4 : offset + 8]
    if not is_box_type(box_type):
        return None
    header = 8
    if size32 == 1:
        if offset + 16 > limit:
            return None
        size = int.from_bytes(data[offset + 8 : offset + 16], "big")
        header = 16
    elif size32 == 0:
        size = limit - offset
    else:
        size = size32
    if size < header or offset + size > limit:
        return None
    return size, header


def walk_boxes(data: bytes, start: int = 0, limit: int | None = None, prefix: str = "") -> list[dict[str, Any]]:
    if limit is None:
        limit = len(data)
    boxes: list[dict[str, Any]] = []
    offset = start
    while offset + 8 <= limit:
        parsed = read_box_size(data, offset, limit)
        if parsed is None:
            break
        size, header = parsed
        box_type = data[offset + 4 : offset + 8].decode("latin-1", errors="replace")
        path = f"{prefix}/{box_type}" if prefix else box_type
        item = {
            "path": path,
            "type": box_type,
            "offset": offset,
            "size": size,
            "header": header,
        }
        boxes.append(item)
        if box_type in CONTAINER_BOXES:
            boxes.extend(walk_boxes(data, offset + header, offset + size, path))
        offset += size
    return boxes


def nal_profile(data: bytes, hook: ModuleType) -> dict[str, Any]:
    nalus = hook.parse_nalus(data)
    type_counts: Counter[str] = Counter()
    layer_counts: Counter[str] = Counter()
    prefix_counts: Counter[str] = Counter()
    payload_lens: list[int] = []
    sequence: list[dict[str, int]] = []
    vps_fields: list[dict[str, int]] = []
    semantics: list[dict[str, Any]] = []
    semantic_kind_counts: Counter[str] = Counter()
    parse_error_counts: Counter[str] = Counter()

    for index, nalu in enumerate(nalus):
        nal_type = hook.nalu_type(data, nalu)
        layer = hook.layer_id(data, nalu)
        payload_len = max(0, nalu.end - nalu.payload_start)
        type_counts[str(nal_type)] += 1
        layer_counts[str(layer)] += 1
        prefix_counts[str(nalu.prefix_len)] += 1
        payload_lens.append(payload_len)
        if len(sequence) < MAX_SEQUENCE_ITEMS:
            sequence.append(
                {
                    "index": index,
                    "type": nal_type,
                    "layer": layer,
                    "payload_len": payload_len,
                    "offset": nalu.start,
                }
            )
        if nal_type == 32:
            body = hook.nalu_body(data, nalu)
            if len(body) >= 2:
                vps_fields.append(
                    {
                        "index": index,
                        "layer": layer,
                        "vps_video_parameter_set_id": hook.get_bits(body, 0, 4),
                        "vps_base_layer_internal_flag": hook.get_bits(body, 4, 1),
                        "vps_base_layer_available_flag": hook.get_bits(body, 5, 1),
                        "vps_max_layers_minus1": hook.get_bits(body, 6, 6),
                        "vps_max_sub_layers_minus1": hook.get_bits(body, 12, 3),
                        "vps_temporal_id_nesting_flag": hook.get_bits(body, 15, 1),
                        "payload_len": payload_len,
                    }
                )
        semantic = parse_nalu_semantics(data, hook, nalu)
        semantic.update(
            {
                "index": index,
                "nal_type": nal_type,
                "layer": layer,
                "payload_len": payload_len,
            }
        )
        semantics.append(semantic)
        semantic_kind_counts[semantic.get("kind", "unknown")] += 1
        if semantic.get("parse_error"):
            parse_error_counts[str(nal_type)] += 1

    first_start = nalus[0].start if nalus else None
    total_payload = sum(payload_lens)
    cross_refs = semantic_cross_references(semantics)
    return {
        "annexb_detected": bool(nalus),
        "total_nalus": len(nalus),
        "bytes_before_first_start": first_start if first_start is not None else len(data),
        "start_code_prefix_counts": dict(sorted(prefix_counts.items())),
        "type_counts": dict(sorted(type_counts.items(), key=lambda kv: int(kv[0]))),
        "layer_counts": dict(sorted(layer_counts.items(), key=lambda kv: int(kv[0]))),
        "unique_types": sorted(int(k) for k in type_counts),
        "unique_layers": sorted(int(k) for k in layer_counts),
        "max_layer": max((int(k) for k in layer_counts), default=None),
        "payload_bytes": total_payload,
        "payload_len_min": min(payload_lens) if payload_lens else None,
        "payload_len_max": max(payload_lens) if payload_lens else None,
        "payload_len_avg": round(total_payload / len(payload_lens), 3) if payload_lens else None,
        "sequence_prefix": sequence,
        "vps_fields": vps_fields[:32],
        "vps_field_count": len(vps_fields),
        "semantics": {
            "kind_counts": dict(sorted(semantic_kind_counts.items())),
            "parse_error_counts_by_type": dict(sorted(parse_error_counts.items(), key=lambda kv: int(kv[0]))),
            "parsed_items": [item for item in semantics if not item.get("parse_error") and item.get("kind") != "other"][:128],
            "parse_errors": [item for item in semantics if item.get("parse_error")][:64],
            "cross_references": cross_refs,
        },
    }


def file_profile(path: Path, hook: ModuleType) -> dict[str, Any]:
    data = path.read_bytes()
    boxes = walk_boxes(data)
    box_counts = Counter(box["type"] for box in boxes)
    return {
        "path": str(path),
        "size": len(data),
        "sha256": sha256_bytes(data),
        "annexb": nal_profile(data, hook),
        "mp4": {
            "box_count": len(boxes),
            "box_type_counts": dict(sorted(box_counts.items())),
            "boxes": boxes[:96],
        },
    }


def parse_named_path(token: str) -> tuple[str, Path]:
    if "=" not in token:
        raise argparse.ArgumentTypeError("--input entries must use NAME=PATH")
    name, path = token.split("=", 1)
    name = name.strip()
    if not name:
        raise argparse.ArgumentTypeError("--input NAME must be non-empty")
    return name, Path(path)


def int_counter_delta(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    keys = sorted({*left, *right}, key=lambda item: int(item) if item.lstrip("-").isdigit() else item)
    return {key: right.get(key, 0) - left.get(key, 0) for key in keys if right.get(key, 0) != left.get(key, 0)}


def compare_annexb(reference: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    ref = reference["annexb"]
    cand = candidate["annexb"]
    ref_types = set(ref["type_counts"])
    cand_types = set(cand["type_counts"])
    ref_layers = set(ref["layer_counts"])
    cand_layers = set(cand["layer_counts"])
    ref_nalus = ref["total_nalus"] or 0
    cand_nalus = cand["total_nalus"] or 0
    return {
        "reference": reference["path"],
        "candidate": candidate["path"],
        "nalu_count_delta": cand_nalus - ref_nalus,
        "nalu_count_ratio_to_reference": round(cand_nalus / ref_nalus, 6) if ref_nalus else None,
        "missing_reference_types": sorted(int(item) for item in ref_types - cand_types),
        "extra_candidate_types": sorted(int(item) for item in cand_types - ref_types),
        "missing_reference_layers": sorted(int(item) for item in ref_layers - cand_layers),
        "extra_candidate_layers": sorted(int(item) for item in cand_layers - ref_layers),
        "type_count_delta": int_counter_delta(ref["type_counts"], cand["type_counts"]),
        "layer_count_delta": int_counter_delta(ref["layer_counts"], cand["layer_counts"]),
        "bytes_before_first_start_delta": cand["bytes_before_first_start"] - ref["bytes_before_first_start"],
        "vps_field_count_delta": cand["vps_field_count"] - ref["vps_field_count"],
    }


def endpoint_exit_code(record: dict[str, Any]) -> int | None:
    probes = record.get("endpoint_probes") or []
    if not probes:
        return None
    exit_code = probes[0].get("exit_code")
    return exit_code if isinstance(exit_code, int) else None


def endpoint_sanitizer_crash(record: dict[str, Any]) -> bool:
    probes = record.get("endpoint_probes") or []
    return bool(probes and probes[0].get("sanitizer_crash") is True)


def variant_record_summary(record: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    annexb = profile["annexb"]
    return {
        "index": record.get("index"),
        "op": record.get("op"),
        "sample": record.get("sample"),
        "d_f_spec_lifted": record.get("d_f_spec_lifted"),
        "reached": record.get("reached"),
        "triggered": record.get("triggered"),
        "endpoint_exit_code": endpoint_exit_code(record),
        "endpoint_sanitizer_crash": endpoint_sanitizer_crash(record),
        "path": record.get("path"),
        "size": profile["size"],
        "total_nalus": annexb["total_nalus"],
        "unique_types": annexb["unique_types"],
        "unique_layers": annexb["unique_layers"],
        "max_layer": annexb["max_layer"],
        "type_counts": annexb["type_counts"],
        "layer_counts": annexb["layer_counts"],
    }


def load_variant_records(records_path: Path, hook: ModuleType, top: int) -> dict[str, Any]:
    records = [json.loads(line) for line in records_path.read_text().splitlines() if line.strip()]
    profiled: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for record in records:
        path = Path(record["path"])
        if not path.exists():
            continue
        profiled.append((record, file_profile(path, hook)))

    best_by_d_f = sorted(
        profiled,
        key=lambda item: (
            item[0].get("d_f_spec_lifted") if item[0].get("d_f_spec_lifted") is not None else 1.0e300,
            item[0].get("index", 1 << 30),
        ),
    )[:top]
    largest_by_nalus = sorted(
        profiled,
        key=lambda item: (
            item[1]["annexb"]["total_nalus"],
            len(item[1]["annexb"]["unique_layers"]),
            item[1]["size"],
        ),
        reverse=True,
    )[:top]
    endpoint_crashes = [record for record, _ in profiled if endpoint_sanitizer_crash(record)]
    return {
        "records_path": str(records_path),
        "record_count": len(records),
        "profiled_count": len(profiled),
        "endpoint_sanitizer_crashes": len(endpoint_crashes),
        "best_by_d_f": [variant_record_summary(record, profile) for record, profile in best_by_d_f],
        "largest_by_nalus": [variant_record_summary(record, profile) for record, profile in largest_by_nalus],
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    hook = load_hook(args.hook)
    inputs = [(name, file_profile(path, hook)) for name, path in args.input]
    input_profiles = {name: profile for name, profile in inputs}

    comparisons: list[dict[str, Any]] = []
    if args.reference:
        if args.reference not in input_profiles:
            raise SystemExit(f"--reference {args.reference!r} is not among --input names")
        reference = input_profiles[args.reference]
        for name, profile in inputs:
            if name == args.reference:
                continue
            item = compare_annexb(reference, profile)
            item["candidate_name"] = name
            item["reference_name"] = args.reference
            comparisons.append(item)

    variant_summary = None
    if args.records:
        variant_summary = load_variant_records(args.records, hook, args.top_variants)
        if args.reference and args.reference in input_profiles:
            ref_profile = input_profiles[args.reference]
            for bucket in ("best_by_d_f", "largest_by_nalus"):
                for item in variant_summary[bucket]:
                    profile = file_profile(Path(item["path"]), hook)
                    item["comparison_to_reference"] = compare_annexb(ref_profile, profile)

    return {
        "schema": "formtrig_gpac3403_hevc_structure_audit_v1",
        "hook": str(args.hook),
        "reference": args.reference,
        "inputs": input_profiles,
        "comparisons": comparisons,
        "variant_summary": variant_summary,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hook", type=Path, default=DEFAULT_HOOK)
    parser.add_argument("--input", action="append", type=parse_named_path, required=True)
    parser.add_argument("--reference", help="Input name used as Annex-B comparison reference.")
    parser.add_argument("--records", type=Path, help="Optional GPAC3403 frontier sweep records.jsonl.")
    parser.add_argument("--top-variants", type=int, default=12)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    if args.top_variants <= 0:
        parser.error("--top-variants must be positive")
    report = build_report(args)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
