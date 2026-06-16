#!/usr/bin/env python3
"""Audit real-CVE candidates for FORMTRIG experiment readiness.

This tool turns local candidate assets into a small machine-readable queue:
which real CVEs already have RNT seeds, binary/uninformative D_T evidence,
terminal validation, TCIR/atoms, harness/build assets, and BindingSpecs.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FIELDS = [
    "rank",
    "target_id",
    "project",
    "category",
    "discovery_rank",
    "readiness",
    "priority",
    "rnt_ready",
    "binary_dt_gap",
    "terminal_validated",
    "validation_signal",
    "binding_spec_present",
    "binding_spec_validated",
    "binding_validation_status",
    "binding_spec_ready",
    "tcir_ready",
    "atom_ready",
    "build_ready",
    "poc_ready",
    "harness_source_ready",
    "seed_count",
    "native_dt_values",
    "source_locations",
    "blockers",
    "next_action",
]


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def intish(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


def cve_records(path: Path) -> dict[str, dict[str, Any]]:
    payload = read_json(path)
    return {
        str(record.get("candidate_id")): record
        for record in payload.get("records", [])
        if record.get("candidate_id")
    }


def discovery_records(path: Path) -> dict[str, dict[str, Any]]:
    payload = read_json(path)
    rows = payload.get("all_targets") or payload.get("top_targets") or []
    return {
        str(record.get("target_id")): record
        for record in rows
        if record.get("source") == "real_cve" and record.get("target_id")
    }


def binding_specs_for(target_id: str, root: Path) -> list[str]:
    if not root.is_dir():
        return []
    return sorted(
        path.name
        for path in root.glob(f"{target_id}.*.yml")
        if ".llm_" not in path.name and not path.name.endswith(".llm_response.yml")
    )


def binding_validation_records(
    target_id: str,
    root: Path = Path("artifacts/formtrig_native_readiness/binding_validation"),
) -> list[dict[str, Any]]:
    if not root.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(root.glob(f"{target_id}*.json")):
        try:
            record = read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if str(record.get("target_id", target_id)) != target_id:
            continue
        record["_path"] = str(path)
        records.append(record)
    return records


def binding_validation_pass(records: list[dict[str, Any]]) -> bool:
    pass_statuses = {"pass", "native_binding_validated", "ready_for_short_gate"}
    for record in records:
        checks = record.get("checks") if isinstance(record.get("checks"), dict) else {}
        if boolish(record.get("ready_for_short_gate")):
            return True
        if str(record.get("status", "")) in pass_statuses:
            return True
        if (
            boolish(record.get("native_site_map_validated"))
            and boolish(checks.get("binding_spec_compile_pass"))
            and boolish(checks.get("lift_audit_pass"))
            and boolish(checks.get("harness_admissibility_pass"))
        ):
            return True
    return False


def binding_validation_status(records: list[dict[str, Any]]) -> str:
    statuses = []
    for record in records:
        status = str(record.get("status") or "unknown")
        path = record.get("_path")
        statuses.append(f"{status}@{path}" if path else status)
    return "; ".join(statuses)


def load_rnt_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except json.JSONDecodeError:
        return {}


def load_rnt_metadata(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def attempt_commands(manifest: dict[str, Any]) -> list[list[str]]:
    commands: list[list[str]] = []
    for attempt in manifest.get("attempts", []):
        command = attempt.get("command")
        if isinstance(command, list) and command:
            commands.append([str(part) for part in command])
    return commands


def first_program(commands: list[list[str]]) -> str:
    for command in commands:
        if command:
            return command[0]
    return ""


def executable_ready(path_text: str) -> bool:
    if not path_text:
        return False
    path = Path(path_text)
    return path.exists() and path.is_file()


def poc_path(project: str, target_id: str) -> Path:
    return Path("benchmarks/cve_pocs") / project / f"{target_id}.poc"


def harness_sources(target_id: str, project: str, program: str) -> list[str]:
    candidates: list[Path] = []
    harness_root = Path("benchmarks/cve_harnesses")
    if not harness_root.is_dir():
        return []
    if project == "libarchive":
        candidates.extend(sorted(harness_root.glob("libarchive*_replay.c")))
    program_name = Path(program).name
    if program_name:
        candidates.extend(sorted(harness_root.glob(f"*{program_name}*.c")))
    candidates.extend(sorted(harness_root.glob(f"*{target_id.lower()}*.c")))
    seen: set[str] = set()
    out: list[str] = []
    for path in candidates:
        text = str(path)
        if text not in seen and path.exists():
            seen.add(text)
            out.append(text)
    return out


def validation_status(path: Path) -> tuple[bool, str, str]:
    if not path.exists():
        return False, "", ""
    text = path.read_text(encoding="utf-8", errors="replace")
    terminal_markers = [
        "SUMMARY: AddressSanitizer",
        "SUMMARY: UndefinedBehaviorSanitizer",
        "runtime error:",
        "SEGV",
        "heap-buffer-overflow",
        "null pointer",
    ]
    returncode_match = re.search(r"^returncode=([-0-9]+)$", text, flags=re.MULTILINE)
    returncode = int(returncode_match.group(1)) if returncode_match else 0
    validated = returncode not in (0, 2) or any(marker in text for marker in terminal_markers)
    signal = ""
    for line in text.splitlines():
        if "SUMMARY: AddressSanitizer" in line or "SUMMARY: UndefinedBehaviorSanitizer" in line:
            signal = line.strip()
            break
        if "runtime error:" in line and not signal:
            signal = line.strip()
    if not signal and returncode_match:
        signal = f"returncode={returncode}"
    return validated, signal, text[:4000]


def atoms_source_locations(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        payload = read_json(path)
    except json.JSONDecodeError:
        return []
    locations: list[str] = []
    for atom in payload.get("atoms", []):
        for location in atom.get("source_locations", []) or []:
            if location and location not in locations:
                locations.append(str(location))
        location = atom.get("source_location")
        if location and location not in locations:
            locations.append(str(location))
    return locations


def audit_target(
    target_id: str,
    cve: dict[str, Any],
    discovery: dict[str, Any],
    binding_spec_dir: Path,
) -> dict[str, Any]:
    project = str(cve.get("project") or discovery.get("project") or "")
    category = str(cve.get("initial_tc_category") or discovery.get("primary_category") or "")
    existing_disposition = str(discovery.get("existing_disposition") or "")
    demoted = (
        discovery.get("lane") == "control_or_negative"
        or existing_disposition.startswith("demote")
    )
    rnt_root = Path("artifacts/rnt_corpus") / target_id
    manifest_path = rnt_root / "manifest.json"
    metadata_path = rnt_root / "metadata.csv"
    manifest = load_rnt_manifest(manifest_path)
    metadata = load_rnt_metadata(metadata_path)
    commands = attempt_commands(manifest)
    program = first_program(commands)
    rnt_ready = (
        manifest.get("metadata_status") == "formal_replay_verified_rnt"
        and intish(manifest.get("unique_rnt_seed_count")) > 0
        and any(boolish(row.get("reached_R")) and not boolish(row.get("triggered_T")) for row in metadata)
    )
    native_dt_values = sorted(
        {
            str(row.get("native_DT"))
            for row in metadata
            if row.get("native_DT") not in (None, "")
        }
    )
    binary_dt_gap = rnt_ready and native_dt_values == ["1"]
    binding_specs = binding_specs_for(target_id, binding_spec_dir)
    binding_spec_present = bool(binding_specs)
    validation_records = binding_validation_records(target_id)
    binding_spec_validated = binding_validation_pass(validation_records)
    binding_status = binding_validation_status(validation_records)
    atom_path = Path("artifacts/atoms") / f"{target_id}.json"
    tcir_path = Path("artifacts/tcir") / f"{target_id}.json"
    trigger_graph_path = Path("artifacts/trigger_graphs") / f"{target_id}.json"
    source_locations = atoms_source_locations(atom_path) or atoms_source_locations(tcir_path)
    validation_path = Path("artifacts/cve_validation_logs") / f"{target_id}.validation.log"
    terminal_validated, validation_signal, validation_excerpt = validation_status(validation_path)
    poc = poc_path(project, target_id)
    harnesses = harness_sources(target_id, project, program)

    blockers: list[str] = []
    if demoted:
        blockers.append(f"existing discovery triage demotes this target: {existing_disposition or discovery.get('lane')}")
    if not rnt_ready:
        blockers.append("no formal RNT seed with R=1,T=0")
    if not binary_dt_gap:
        blockers.append("binary native D_T gap is not established")
    if not terminal_validated:
        blockers.append("terminal validation is missing or inconclusive")
    if not binding_spec_present:
        blockers.append("no executable BindingSpec candidate")
    elif not binding_spec_validated:
        blockers.append("BindingSpec candidate is not native-site-map validated")
    if not tcir_path.exists():
        blockers.append("no TCIR file")
    if not atom_path.exists():
        blockers.append("no atom file")
    if not executable_ready(program):
        blockers.append("program binary is missing locally")
    if not poc.exists():
        blockers.append("PoC file is missing locally")

    if demoted:
        readiness = "control_or_negative"
        next_action = "keep as control/sanity evidence; do not spend main real-CVE long-run budget"
        priority = 95
    elif rnt_ready and binary_dt_gap and terminal_validated and binding_spec_validated:
        readiness = "ready_for_formtrig_short_gate"
        next_action = "run FORMTRIG seed-readiness/gate and matched AFL++ family short baselines"
        priority = 10
    elif rnt_ready and binary_dt_gap and terminal_validated and binding_spec_present:
        readiness = "needs_binding_validation"
        next_action = "build a FORMTRIG-instrumented target/site map, compile BindingSpec, run lift audit and harness admissibility"
        priority = 15
    elif rnt_ready and binary_dt_gap and terminal_validated:
        readiness = "ready_for_binding_spec"
        next_action = "draft BindingSpec from TCIR/atoms and validate static/dynamic binding signal"
        priority = 20
    elif rnt_ready and binary_dt_gap:
        readiness = "needs_terminal_validation_and_binding"
        next_action = "confirm terminal PoC/replay, then draft BindingSpec"
        priority = 30
    elif rnt_ready:
        readiness = "needs_dt_gap_audit"
        next_action = "audit native D_T and trigger oracle before BindingSpec work"
        priority = 50
    else:
        readiness = "not_ready"
        next_action = "collect formal RNT seed before spending fuzzing budget"
        priority = 80

    return {
        "target_id": target_id,
        "project": project,
        "category": category,
        "discovery_rank": discovery.get("rank"),
        "readiness": readiness,
        "priority": priority,
        "existing_disposition": existing_disposition,
        "discovery_lane": discovery.get("lane"),
        "rnt_ready": rnt_ready,
        "binary_dt_gap": binary_dt_gap,
        "terminal_validated": terminal_validated,
        "validation_signal": validation_signal,
        "binding_spec_present": binding_spec_present,
        "binding_spec_validated": binding_spec_validated,
        "binding_validation_status": binding_status,
        "binding_spec_ready": binding_spec_validated,
        "tcir_ready": tcir_path.exists(),
        "atom_ready": atom_path.exists(),
        "trigger_graph_ready": trigger_graph_path.exists(),
        "build_ready": executable_ready(program),
        "poc_ready": poc.exists(),
        "harness_source_ready": bool(harnesses),
        "seed_count": intish(manifest.get("unique_rnt_seed_count")),
        "native_dt_values": ",".join(native_dt_values),
        "source_locations": "; ".join(source_locations),
        "blockers": "; ".join(blockers),
        "next_action": next_action,
        "paths": {
            "program": program,
            "poc": str(poc),
            "rnt_manifest": str(manifest_path),
            "rnt_metadata": str(metadata_path),
            "binding_specs": binding_specs,
            "binding_validation_records": [record.get("_path", "") for record in validation_records],
            "atom": str(atom_path),
            "tcir": str(tcir_path),
            "trigger_graph": str(trigger_graph_path),
            "validation_log": str(validation_path),
            "harness_sources": harnesses,
        },
        "validation_excerpt": validation_excerpt,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=FIELDS,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in FIELDS})


def csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# FORMTRIG Real-CVE Readiness Audit",
        "",
        "This audit checks whether the real-CVE candidates are executable enough",
        "to enter FORMTRIG short-gate work. It separates the RNT/binary-D_T",
        "benefit opportunity from missing engineering assets such as BindingSpec",
        "or terminal validation.",
        "",
        "| rank | target | category | readiness | RNT | binary `D_T` gap | terminal | BindingSpec candidate | BindingSpec validated | next action |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {rank} | {target_id} | {category} | `{readiness}` | {rnt} | {dt} | {term} | {binding_present} | {binding_validated} | {next_action} |".format(
                rank=row.get("rank", ""),
                target_id=row.get("target_id", ""),
                category=row.get("category", ""),
                readiness=row.get("readiness", ""),
                rnt="yes" if row.get("rnt_ready") else "no",
                dt="yes" if row.get("binary_dt_gap") else "no",
                term="yes" if row.get("terminal_validated") else "no",
                binding_present="yes" if row.get("binding_spec_present") else "no",
                binding_validated="yes" if row.get("binding_spec_validated") else "no",
                next_action=str(row.get("next_action", "")).replace("|", "\\|"),
            )
        )

    lines.extend(["", "## Details", ""])
    for row in rows:
        lines.extend(
            [
                f"### {row.get('rank')}. {row.get('target_id')}",
                "",
                f"- Discovery rank: {row.get('discovery_rank')}",
                f"- Source locations: {row.get('source_locations') or 'none'}",
                f"- Native D_T values in RNT metadata: `{row.get('native_dt_values') or 'none'}`",
                f"- Terminal validation signal: {row.get('validation_signal') or 'none'}",
                f"- Binding validation status: {row.get('binding_validation_status') or 'none'}",
                f"- Blockers: {row.get('blockers') or 'none'}",
                f"- Program: `{row.get('paths', {}).get('program', '')}`",
                f"- RNT manifest: `{row.get('paths', {}).get('rnt_manifest', '')}`",
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cve-inventory", type=Path, default=Path("artifacts/cve_bench_candidate_audit.json"))
    parser.add_argument("--discovery", type=Path, default=Path("artifacts/formtrig_native_readiness/hard_target_discovery_queue_20260616.json"))
    parser.add_argument("--binding-spec-dir", type=Path, default=Path("artifacts/binding_specs"))
    parser.add_argument("--target-id", action="append", default=[])
    parser.add_argument("--out-json", required=True, type=Path)
    parser.add_argument("--out-csv", required=True, type=Path)
    parser.add_argument("--out-md", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cves = cve_records(args.cve_inventory)
    discovery = discovery_records(args.discovery)
    target_ids = args.target_id or [
        target_id
        for target_id, record in sorted(
            discovery.items(),
            key=lambda item: intish(item[1].get("rank"), 999),
        )
        if target_id in cves
    ]
    rows = [
        audit_target(target_id, cves[target_id], discovery.get(target_id, {}), args.binding_spec_dir)
        for target_id in target_ids
        if target_id in cves
    ]
    rows.sort(key=lambda row: (intish(row.get("priority"), 999), intish(row.get("discovery_rank"), 999), row["target_id"]))
    for index, row in enumerate(rows, 1):
        row["rank"] = index
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inputs": {
            "cve_inventory": str(args.cve_inventory),
            "discovery": str(args.discovery),
            "binding_spec_dir": str(args.binding_spec_dir),
        },
        "target_count": len(rows),
        "targets": rows,
    }
    write_json(args.out_json, payload)
    write_csv(args.out_csv, rows)
    write_markdown(args.out_md, rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
