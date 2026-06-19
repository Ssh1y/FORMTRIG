#!/usr/bin/env python3
"""Package GPAC_3403 typed-retained candidate audit evidence.

Typed retention preserves FORMTRIG candidates that reached TC-rooted lifted
signal but were not saved by the normal AFL++ queue.  This packager joins the
retention summary, HEVC structure audit, and optional endpoint stderr audit into
one run-local JSON file so R2T progress claims can be checked from a single
artifact.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
STRUCTURE_AUDIT = REPO_ROOT / "tools" / "gpac3403_hevc_structure_audit.py"
ENDPOINT_AUDIT = REPO_ROOT / "tools" / "gpac3403_endpoint_signature_audit.py"
DEFAULT_HOOK = REPO_ROOT / "scripts" / "formtrig_hooks" / "hevc_annexb_structure_hook.py"


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def compact_typed_summary(summary: dict[str, Any] | None) -> dict[str, Any]:
    if summary is None:
        return {
            "available": False,
            "reason": "typed_retained_summary.json is missing",
        }
    keys = [
        "schema",
        "records_tsv",
        "missing_records_tsv",
        "records_jsonl",
        "retained_records",
        "existing_inputs",
        "missing_inputs",
        "total_existing_bytes",
        "hook_used_records",
        "roles",
        "component_kinds",
        "ops",
        "source_queue_ids",
        "d_f_spec_lifted",
        "best_by_d_f",
        "largest_by_size",
        "missing_examples",
    ]
    return {
        "available": True,
        **{key: summary.get(key) for key in keys if key in summary},
    }


def parse_named_path(token: str) -> tuple[str, Path]:
    if "=" not in token:
        raise argparse.ArgumentTypeError("entries must use NAME=PATH")
    name, path = token.split("=", 1)
    name = name.strip()
    if not name:
        raise argparse.ArgumentTypeError("NAME must be non-empty")
    return name, Path(path)


def records_jsonl_line_count(path: Path | None) -> int | None:
    if path is None or not path.is_file():
        return None
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def build_structure_audit(
    records_jsonl: Path | None,
    hook_path: Path,
    structure_inputs: list[tuple[str, Path]],
    structure_reference: str | None,
    top: int,
) -> dict[str, Any]:
    if records_jsonl is None or not records_jsonl.is_file():
        return {
            "available": False,
            "reason": "typed_retained_records.jsonl is missing",
        }

    structure = load_module(STRUCTURE_AUDIT, "gpac3403_hevc_structure_audit_for_package")
    if structure_inputs:
        args = argparse.Namespace(
            hook=hook_path,
            input=structure_inputs,
            reference=structure_reference,
            records=records_jsonl,
            top_variants=top,
        )
        report = structure.build_report(args)
        return {
            "available": True,
            "mode": "records_with_named_inputs",
            "report": report,
        }

    hook = structure.load_hook(hook_path)
    variant_summary = structure.load_variant_records(records_jsonl, hook, top)
    return {
        "available": True,
        "mode": "records_only",
        "variant_summary": variant_summary,
    }


def infer_endpoint_logs(run_dir: Path, provided: Path | None) -> Path | None:
    if provided is not None:
        return provided
    candidate = run_dir / "logs"
    if candidate.is_dir():
        return candidate
    return None


def build_endpoint_audit(
    logs_dir: Path | None,
    endpoint_summary: Path | None,
    include_records: bool,
) -> dict[str, Any]:
    if logs_dir is None:
        return {
            "available": False,
            "reason": "endpoint logs directory is not configured",
        }
    if not logs_dir.is_dir():
        return {
            "available": False,
            "logs_dir": str(logs_dir),
            "reason": "endpoint logs directory is missing",
        }
    endpoint = load_module(ENDPOINT_AUDIT, "gpac3403_endpoint_signature_audit_for_package")
    files = endpoint.endpoint_stderr_files(logs_dir)
    if not files:
        return {
            "available": False,
            "logs_dir": str(logs_dir),
            "reason": "endpoint logs directory has no endpoint stderr files",
        }
    args = argparse.Namespace(
        logs_dir=logs_dir,
        summary=endpoint_summary,
        include_records=include_records,
        exclude_other=True,
    )
    return {
        "available": True,
        "logs_dir": str(logs_dir),
        "stderr_files": len(files),
        "report": endpoint.build_report(args),
    }


def assess_evidence(
    typed_summary: dict[str, Any] | None,
    records_jsonl: Path | None,
    structure_audit: dict[str, Any],
    endpoint_audit: dict[str, Any],
) -> dict[str, Any]:
    retained_records = int((typed_summary or {}).get("retained_records") or 0)
    existing_inputs = int((typed_summary or {}).get("existing_inputs") or 0)
    d_f = (typed_summary or {}).get("d_f_spec_lifted") or {}
    records_lines = records_jsonl_line_count(records_jsonl)

    structure_profiled = 0
    if structure_audit.get("available"):
        if "variant_summary" in structure_audit:
            structure_profiled = int(structure_audit["variant_summary"].get("profiled_count") or 0)
        else:
            variant_summary = (
                structure_audit.get("report", {})
                .get("variant_summary")
                or {}
            )
            structure_profiled = int(variant_summary.get("profiled_count") or 0)

    endpoint_variant_files = 0
    endpoint_positive_files = 0
    positive_only: list[str] = []
    if endpoint_audit.get("available"):
        report = endpoint_audit.get("report", {})
        endpoint_variant_files = int(report.get("variant", {}).get("files") or 0)
        endpoint_positive_files = int(report.get("positive_control", {}).get("files") or 0)
        positive_only = list(
            report.get("contrast", {}).get("positive_control_signatures_absent_from_variants") or []
        )

    if retained_records == 0:
        claim_boundary = (
            "No typed-retained candidates were captured; this run only proves "
            "retention/audit wiring, not R2T guidance benefit."
        )
    elif structure_profiled == 0:
        claim_boundary = (
            "Typed-retained candidates exist but none were structurally profiled; "
            "do not claim endpoint proximity from this package alone."
        )
    elif endpoint_variant_files == 0:
        claim_boundary = (
            "Typed-retained candidates were structurally profiled, but endpoint "
            "replay evidence is absent; claims are limited to pre-endpoint structure."
        )
    else:
        claim_boundary = (
            "Typed-retained candidates have structure and endpoint evidence; "
            "compare variant signatures against positive-control gaps before "
            "claiming R2T progress."
        )

    return {
        "retained_records": retained_records,
        "existing_inputs": existing_inputs,
        "records_jsonl_lines": records_lines,
        "d_f_spec_lifted_count": d_f.get("count"),
        "d_f_spec_lifted_min": d_f.get("min"),
        "d_f_spec_lifted_max": d_f.get("max"),
        "structure_profiled_candidates": structure_profiled,
        "endpoint_variant_files": endpoint_variant_files,
        "endpoint_positive_control_files": endpoint_positive_files,
        "positive_control_signatures_absent_from_variants": positive_only,
        "claim_boundary": claim_boundary,
    }


def build_package(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = args.run_dir.resolve()
    typed_summary_path = args.typed_summary or run_dir / "typed_retained_summary.json"
    records_jsonl = args.records_jsonl or run_dir / "typed_retained_records.jsonl"
    endpoint_logs_dir = infer_endpoint_logs(run_dir, args.endpoint_logs_dir)
    typed_summary = read_json(typed_summary_path)

    structure_audit = build_structure_audit(
        records_jsonl,
        args.hook,
        args.structure_input or [],
        args.structure_reference,
        args.top,
    )
    endpoint_audit = build_endpoint_audit(
        endpoint_logs_dir,
        args.endpoint_summary,
        args.include_endpoint_records,
    )
    return {
        "schema": "formtrig_gpac3403_typed_retained_audit_package_v1",
        "run_dir": str(run_dir),
        "typed_summary_path": str(typed_summary_path),
        "records_jsonl_path": str(records_jsonl),
        "typed_retained": compact_typed_summary(typed_summary),
        "structure_audit": structure_audit,
        "endpoint_audit": endpoint_audit,
        "evidence_assessment": assess_evidence(
            typed_summary,
            records_jsonl,
            structure_audit,
            endpoint_audit,
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--typed-summary", type=Path)
    parser.add_argument("--records-jsonl", type=Path)
    parser.add_argument("--hook", type=Path, default=DEFAULT_HOOK)
    parser.add_argument("--structure-input", action="append", type=parse_named_path)
    parser.add_argument("--structure-reference")
    parser.add_argument("--endpoint-logs-dir", type=Path)
    parser.add_argument("--endpoint-summary", type=Path)
    parser.add_argument("--include-endpoint-records", action="store_true")
    parser.add_argument("--top", type=int, default=8)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    if args.top <= 0:
        parser.error("--top must be positive")
    if args.structure_reference and not args.structure_input:
        parser.error("--structure-reference requires --structure-input")

    package = build_package(args)
    rendered = json.dumps(package, indent=2, sort_keys=True) + "\n"
    out = args.out or args.run_dir / "typed_retained_audit_package.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
