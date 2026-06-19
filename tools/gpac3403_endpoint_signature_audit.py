#!/usr/bin/env python3
"""Audit GPAC_3403 endpoint stderr signatures against the positive control."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
VARIANT_RE = re.compile(r"variant_(\d+)\.endpoint_(\d+)\.stderr$")

SIGNATURES: dict[str, re.Pattern[str]] = {
    "wrong_output_layer_sets": re.compile(r"Wrong number of output layer sets in VPS\s+(\d+),\s+max\s+(\d+)\s+supported"),
    "failed_vps_extensions": re.compile(r"Failed to parse VPS extensions"),
    "layers_only_4": re.compile(r"(\d+)\s+layers in VPS but only\s+(\d+)\s+supported in GPAC"),
    "vps_max_layer_id": re.compile(r"VPS max layer ID\s+(\d+)\s+but GPAC only supports\s+(\d+)"),
    "video_param_set_error": re.compile(r"Error parsing Video Param Set"),
    "sequence_param_set_error": re.compile(r"Error parsing Sequence Param Set"),
    "picture_param_set_error": re.compile(r"Error parsing Picture Param Set"),
    "nal_type_32_error": re.compile(r"Error parsing NAL unit type 32"),
    "nal_type_49_not_handled": re.compile(r"NAL Unit type 49 not handled"),
    "track_importing_hevc": re.compile(r"Track Importing HEVC"),
    "hevc_import_results": re.compile(r"HEVC Import results:\s+(\d+)\s+samples\s+\((\d+)\s+NALUs\)"),
    "lhevc_import_results": re.compile(r"HEVC L-HEVC Import results:\s+Slices:\s+(\d+)\s+I\s+(\d+)\s+P\s+(\d+)\s+B"),
    "asan": re.compile(r"AddressSanitizer|SUMMARY: AddressSanitizer"),
    "asan_double_free": re.compile(r"AddressSanitizer: attempting double-free|SUMMARY: AddressSanitizer: double-free|double[- ]free"),
}


def clean_stderr(text: str) -> str:
    return ANSI_RE.sub("", text)


def classify_log(path: Path) -> dict[str, Any]:
    match = VARIANT_RE.search(path.name)
    if match:
        return {
            "kind": "variant",
            "variant_index": int(match.group(1)),
            "rep": int(match.group(2)),
        }
    if path.name.startswith("positive_control.endpoint_") and path.name.endswith(".stderr"):
        rep_match = re.search(r"endpoint_(\d+)\.stderr$", path.name)
        return {
            "kind": "positive_control",
            "variant_index": None,
            "rep": int(rep_match.group(1)) if rep_match else None,
        }
    return {
        "kind": "other",
        "variant_index": None,
        "rep": None,
    }


def analyze_text(text: str) -> dict[str, Any]:
    clean = clean_stderr(text)
    signatures: dict[str, Any] = {}
    for name, pattern in SIGNATURES.items():
        matches = list(pattern.finditer(clean))
        values = [match.groups() for match in matches if match.groups()]
        signatures[name] = {
            "present": bool(matches),
            "occurrences": len(matches),
            "values": values[:32],
        }
    return signatures


def read_summary(summary_path: Path | None) -> dict[str, Any] | None:
    if summary_path is None:
        return None
    return json.loads(summary_path.read_text(encoding="utf-8"))


def endpoint_stderr_files(logs_dir: Path) -> list[Path]:
    return sorted(path for path in logs_dir.glob("*.endpoint_*.stderr") if path.is_file())


def summarize_import_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    hevc_observations = []
    lhevc_observations = []
    double_free_records = []
    for record in records:
        for samples, nalus in record["signatures"]["hevc_import_results"]["values"]:
            hevc_observations.append(
                {
                    "path": record["path"],
                    "samples": int(samples),
                    "nalus": int(nalus),
                }
            )
        for i_slices, p_slices, b_slices in record["signatures"]["lhevc_import_results"]["values"]:
            lhevc_observations.append(
                {
                    "path": record["path"],
                    "i_slices": int(i_slices),
                    "p_slices": int(p_slices),
                    "b_slices": int(b_slices),
                }
            )
        if record["signatures"]["asan_double_free"]["present"]:
            double_free_records.append(record)

    return {
        "hevc_import_observations": len(hevc_observations),
        "hevc_import_files": len({obs["path"] for obs in hevc_observations}),
        "hevc_samples_max": max((obs["samples"] for obs in hevc_observations), default=None),
        "hevc_nalus_max": max((obs["nalus"] for obs in hevc_observations), default=None),
        "hevc_top_samples": sorted(
            hevc_observations,
            key=lambda obs: (obs["samples"], obs["nalus"], obs["path"]),
            reverse=True,
        )[:8],
        "lhevc_import_observations": len(lhevc_observations),
        "lhevc_import_files": len({obs["path"] for obs in lhevc_observations}),
        "lhevc_top_slices": sorted(
            lhevc_observations,
            key=lambda obs: (obs["i_slices"] + obs["p_slices"] + obs["b_slices"], obs["path"]),
            reverse=True,
        )[:8],
        "asan_double_free_files": len(double_free_records),
        "asan_double_free_examples": [record["path"] for record in double_free_records[:8]],
    }


def summarize_group(records: list[dict[str, Any]]) -> dict[str, Any]:
    per_signature: dict[str, Any] = {}
    for name in SIGNATURES:
        files_with_signature = [record for record in records if record["signatures"][name]["present"]]
        occurrences = sum(record["signatures"][name]["occurrences"] for record in records)
        value_counter: Counter[str] = Counter()
        for record in files_with_signature:
            for values in record["signatures"][name]["values"]:
                value_counter["/".join(values)] += 1
        per_signature[name] = {
            "files": len(files_with_signature),
            "occurrences": occurrences,
            "top_values": [{"value": value, "count": count} for value, count in value_counter.most_common(12)],
            "examples": [record["path"] for record in files_with_signature[:8]],
        }
    return {
        "files": len(records),
        "metrics": summarize_import_metrics(records),
        "signatures": per_signature,
    }


def compact_summary(summary: dict[str, Any] | None) -> dict[str, Any] | None:
    if summary is None:
        return None
    keys = [
        "generated_variants",
        "endpoint_replayed_variants",
        "reached",
        "rnt",
        "triggered",
        "endpoint_sanitizer_crashes",
        "endpoint_native_crashes",
        "runtime_timeouts",
        "endpoint_timeouts",
        "d_f_spec_lifted_min",
        "d_f_spec_lifted_max",
        "duration_s",
    ]
    return {key: summary.get(key) for key in keys if key in summary}


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    summary = read_summary(args.summary)
    records = []
    for path in endpoint_stderr_files(args.logs_dir):
        classification = classify_log(path)
        if args.exclude_other and classification["kind"] == "other":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        records.append(
            {
                "path": str(path),
                **classification,
                "signatures": analyze_text(text),
            }
        )

    variant_records = [record for record in records if record["kind"] == "variant"]
    positive_records = [record for record in records if record["kind"] == "positive_control"]
    variant_summary = summarize_group(variant_records)
    positive_summary = summarize_group(positive_records)
    variant_sig = variant_summary["signatures"]
    positive_sig = positive_summary["signatures"]
    positive_only = [
        name
        for name in SIGNATURES
        if positive_sig[name]["files"] > 0 and variant_sig[name]["files"] == 0
    ]

    return {
        "schema": "formtrig_gpac3403_endpoint_signature_audit_v2",
        "logs_dir": str(args.logs_dir),
        "summary": compact_summary(summary),
        "records": records if args.include_records else None,
        "variant": variant_summary,
        "positive_control": positive_summary,
        "contrast": {
            "positive_control_signatures_absent_from_variants": positive_only,
            "variant_files": variant_summary["files"],
            "positive_control_files": positive_summary["files"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs-dir", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--include-records", action="store_true")
    parser.add_argument("--exclude-other", action="store_true", default=True)
    args = parser.parse_args(argv)

    report = build_report(args)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
