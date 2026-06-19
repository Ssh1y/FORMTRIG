#!/usr/bin/env python3
"""Build the Magma binary-state TC cohort used by FORMTRIG experiments."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_CATEGORY = "binary-state-null"


def read_inventory(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".csv":
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    records = payload.get("records") if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        raise ValueError(f"inventory must contain a records list: {path}")
    return [row for row in records if isinstance(row, dict)]


def read_rnt_records(path: Path) -> dict[str, dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    records = payload.get("records") if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        raise ValueError(f"RNT status must contain a records list: {path}")
    magma: dict[str, dict[str, Any]] = {}
    for row in records:
        if not isinstance(row, dict):
            continue
        if str(row.get("suite") or "") != "magma":
            continue
        target_id = str(row.get("target_id") or "")
        if target_id:
            magma[target_id] = row
    return magma


def is_true(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def cohort_role(row: dict[str, Any], rnt: dict[str, Any]) -> str:
    status = str(rnt.get("status") or "missing_rnt_status")
    if status == "formal_ready":
        if (
            str(row.get("classification_confidence") or "") == "known_manifest"
            and not is_true(row.get("ambiguous"))
        ):
            return "strict_clean_binary_candidate"
        return "formal_ready_binary_candidate"
    if status == "excluded":
        return "harness_repair_or_runner_gap"
    return "metadata_gap"


def build_cohort(
    inventory_path: Path,
    rnt_status_path: Path,
    *,
    category: str = DEFAULT_CATEGORY,
) -> dict[str, Any]:
    inventory = read_inventory(inventory_path)
    rnt_by_target = read_rnt_records(rnt_status_path)
    rows = [
        row
        for row in inventory
        if str(row.get("primary_tc_category") or row.get("tc_category") or "") == category
    ]

    records: list[dict[str, Any]] = []
    for row in rows:
        target_id = str(row.get("target_id") or row.get("bug_id") or "")
        rnt = rnt_by_target.get(target_id, {})
        status = str(rnt.get("status") or "missing_rnt_status")
        records.append(
            {
                "target_id": target_id,
                "project": str(row.get("project") or ""),
                "program": str(row.get("program") or ""),
                "primary_tc_category": str(row.get("primary_tc_category") or row.get("tc_category") or ""),
                "secondary_tc_category": str(row.get("secondary_tc_category") or ""),
                "ambiguous": is_true(row.get("ambiguous")),
                "classification_confidence": str(row.get("classification_confidence") or ""),
                "canary_expression": str(row.get("canary_expression") or ""),
                "target_location": str(row.get("target_location") or ""),
                "observation_point": str(row.get("observation_point") or ""),
                "rnt_status": status,
                "rnt_seed_files": int(str(rnt.get("seed_files") or "0") or 0),
                "rnt_reached_rows": int(str(rnt.get("reached_rows") or "0") or 0),
                "rnt_triggered_rows": int(str(rnt.get("triggered_rows") or "0") or 0),
                "blocking_reason": str(rnt.get("blocking_reason") or ""),
                "cohort_role": cohort_role(row, rnt),
                "main_experiment_eligible": status == "formal_ready",
                "strict_clean_binary": (
                    status == "formal_ready"
                    and str(row.get("classification_confidence") or "") == "known_manifest"
                    and not is_true(row.get("ambiguous"))
                ),
                "patch_path": str(row.get("patch_path") or ""),
            }
        )

    status_counts = Counter(record["rnt_status"] for record in records)
    role_counts = Counter(record["cohort_role"] for record in records)
    project_counts = Counter(record["project"] for record in records)
    eligible = [record for record in records if record["main_experiment_eligible"]]
    strict = [record for record in records if record["strict_clean_binary"]]
    ambiguous = [record for record in records if record["ambiguous"]]

    return {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "category": category,
        "inputs": {
            "inventory": str(inventory_path),
            "rnt_status": str(rnt_status_path),
        },
        "summary": {
            "inventory_binary_total": len(records),
            "main_experiment_eligible": len(eligible),
            "excluded_or_blocked": status_counts.get("excluded", 0),
            "strict_clean_binary": len(strict),
            "ambiguous_or_secondary": len(ambiguous),
            "status_counts": dict(sorted(status_counts.items())),
            "role_counts": dict(sorted(role_counts.items())),
            "project_counts": dict(sorted(project_counts.items())),
        },
        "methodology": {
            "main_claim_rule": (
                "Use main_experiment_eligible targets for Magma binary-state claims; they have formal RNT "
                "seeds with R>0,T=0 and can support R2T long runs."
            ),
            "excluded_rule": (
                "Excluded targets remain useful harness-repair opportunities, but they should not be counted "
                "as FORMTRIG failures or baseline wins until the runner reaches the target path."
            ),
            "strict_clean_binary_rule": (
                "strict_clean_binary keeps only non-ambiguous known-manifest null/pointer-state predicates; "
                "the broader eligible cohort includes compound binary-rooted cases needed for generality."
            ),
        },
        "records": records,
    }


def md_cell(value: Any) -> str:
    text = str(value)
    text = text.replace("\n", " ")
    text = text.replace("|", "\\|")
    return text


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    records = payload["records"]
    eligible = [record for record in records if record["main_experiment_eligible"]]
    excluded = [record for record in records if record["rnt_status"] == "excluded"]
    strict = [record for record in records if record["strict_clean_binary"]]

    lines = [
        "# Magma Binary-State TC Cohort",
        "",
        f"Generated UTC: {payload['generated_at_utc']}",
        "",
        "## Summary",
        "",
        "| metric | value |",
        "|---|---:|",
        f"| inventory_binary_total | {summary['inventory_binary_total']} |",
        f"| main_experiment_eligible | {summary['main_experiment_eligible']} |",
        f"| excluded_or_blocked | {summary['excluded_or_blocked']} |",
        f"| strict_clean_binary | {summary['strict_clean_binary']} |",
        f"| ambiguous_or_secondary | {summary['ambiguous_or_secondary']} |",
        "",
        "## Formal-Ready Binary Targets",
        "",
        "| target | project | program | confidence | secondary | expression |",
        "|---|---|---|---|---|---|",
    ]
    for record in eligible:
        lines.append(
            "| {target_id} | {project} | {program} | {confidence} | {secondary} | `{expr}` |".format(
                target_id=md_cell(record["target_id"]),
                project=md_cell(record["project"]),
                program=md_cell(record["program"]),
                confidence=md_cell(record["classification_confidence"]),
                secondary=md_cell(record["secondary_tc_category"] or ""),
                expr=md_cell(record["canary_expression"]),
            )
        )

    lines.extend(
        [
            "",
            "## Excluded Harness/Runner Gaps",
            "",
            "| target | project | program | reason |",
            "|---|---|---|---|",
        ]
    )
    for record in excluded:
        lines.append(
            "| {target_id} | {project} | {program} | {reason} |".format(
                target_id=md_cell(record["target_id"]),
                project=md_cell(record["project"]),
                program=md_cell(record["program"]),
                reason=md_cell(record["blocking_reason"]),
            )
        )

    lines.extend(
        [
            "",
            "## Strict Clean Binary Subset",
            "",
            "| target | project | expression |",
            "|---|---|---|",
        ]
    )
    for record in strict:
        lines.append(
            "| {target_id} | {project} | `{expr}` |".format(
                target_id=md_cell(record["target_id"]),
                project=md_cell(record["project"]),
                expr=md_cell(record["canary_expression"]),
            )
        )

    lines.extend(
        [
            "",
            "## Methodology Notes",
            "",
            f"- {payload['methodology']['main_claim_rule']}",
            f"- {payload['methodology']['excluded_rule']}",
            f"- {payload['methodology']['strict_clean_binary_rule']}",
            "",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=Path("artifacts/magma_canary_inventory.json"))
    parser.add_argument("--rnt-status", type=Path, default=Path("artifacts/rnt_corpus_status.json"))
    parser.add_argument("--category", default=DEFAULT_CATEGORY)
    parser.add_argument("--out-json", type=Path, default=Path("artifacts/magma_binary_tc_cohort.json"))
    parser.add_argument("--out-md", type=Path, default=Path("artifacts/magma_binary_tc_cohort.md"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_cohort(args.inventory, args.rnt_status, category=args.category)
    write_json(args.out_json, payload)
    write_markdown(args.out_md, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
