#!/usr/bin/env python3
"""Plan the next FORMTRIG hard-target discovery runs.

The planner is benefit-first: it ranks targets by whether they can plausibly
show a user-visible FORMTRIG advantage on binary or otherwise uninformative
trigger conditions, then emits the shortest next experiment needed to prove or
discard that opportunity.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FIELDS = [
    "rank",
    "target_id",
    "source",
    "project",
    "primary_category",
    "secondary_category",
    "score",
    "lane",
    "status",
    "binding_spec",
    "binding_spec_validated",
    "existing_disposition",
    "benefit_hypothesis",
    "blockers",
    "next_action",
    "suggested_short_triage",
    "source_evidence",
]


CATEGORY_SCORE = {
    "compound-sequence-lifecycle": 36,
    "binary-state-null": 32,
    "equality/magic": 10,
    "numeric-margin": 4,
}


SECONDARY_SCORE = {
    "compound-sequence-lifecycle": 16,
    "binary-state-null": 12,
    "equality/magic": 4,
    "numeric-margin": 2,
}


SOURCE_BASE_SCORE = {
    "real_cve": 42,
    "magma": 24,
}


DEMOTE_DISPOSITIONS = {
    "demote_to_control_or_negative",
    "demote_harness_artifact",
}


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


def split_links(value: Any) -> list[str]:
    return [part for part in str(value or "").replace(",", ";").split(";") if part.strip()]


def normalize_category(value: Any) -> str:
    return str(value or "").strip()


def binding_specs_for(target_id: str, binding_spec_dir: Path | None) -> list[str]:
    if binding_spec_dir is None or not binding_spec_dir.is_dir():
        return []
    specs: list[str] = []
    for path in binding_spec_dir.glob(f"{target_id}.*.yml"):
        if ".llm_" in path.name or path.name.endswith(".llm_response.yml"):
            continue
        specs.append(path.name)
    return sorted(specs)


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
        if str(record.get("target_id", target_id)) == target_id:
            schema = str(record.get("schema", ""))
            if schema and schema != "formtrig_binding_candidate_validation_v1":
                continue
            if not schema and not any(
                key in record
                for key in (
                    "binding_spec",
                    "ready_for_short_gate",
                    "native_site_map_validated",
                    "checks",
                )
            ):
                continue
            records.append(record)
    return records


def binding_spec_validated(target_id: str) -> bool:
    pass_statuses = {"pass", "native_binding_validated", "ready_for_short_gate"}
    for record in binding_validation_records(target_id):
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


def comparison_targets(comparison_root: Path | None) -> Counter[str]:
    counts: Counter[str] = Counter()
    if comparison_root is None or not comparison_root.exists():
        return counts
    paths = [comparison_root] if comparison_root.name == "comparison.json" else sorted(comparison_root.glob("*/comparison.json"))
    for path in paths:
        try:
            payload = read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        target_id = str(payload.get("target_id") or "")
        if target_id:
            counts[target_id] += 1
    return counts


def existing_dispositions(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    payload = read_json(path)
    return {
        str(row.get("target_id")): row
        for row in payload.get("targets", [])
        if row.get("target_id")
    }


def category_terms(primary: str, secondary: str) -> list[str]:
    return [value for value in [primary, secondary] if value]


def hard_category(primary: str, secondary: str) -> bool:
    categories = set(category_terms(primary, secondary))
    return bool(categories & {"binary-state-null", "compound-sequence-lifecycle"})


def direct_comparison_category(primary: str, secondary: str) -> bool:
    categories = set(category_terms(primary, secondary))
    return (
        categories <= {"numeric-margin"}
        or categories <= {"equality/magic"}
        or categories <= {"numeric-margin", "equality/magic"}
    )


def score_categories(primary: str, secondary: str) -> int:
    score = CATEGORY_SCORE.get(primary, 0)
    if secondary and secondary != primary:
        score += SECONDARY_SCORE.get(secondary, 0)
    if direct_comparison_category(primary, secondary):
        score -= 18
    return score


def benefit_hypothesis(source: str, primary: str, secondary: str) -> str:
    categories = set(category_terms(primary, secondary))
    if "compound-sequence-lifecycle" in categories and "binary-state-null" in categories:
        return "binary terminal state is gated by parser/object lifecycle progress that CmpLog-style direct comparison feedback may not expose"
    if "compound-sequence-lifecycle" in categories:
        return "terminal success depends on event order, object identity, or parser state rather than one scalar branch distance"
    if "binary-state-null" in categories:
        return "native trigger feedback is likely 0/1, so FORMTRIG can test whether lifted producer/use or lifecycle features guide R2T"
    if "equality/magic" in categories:
        return "exact-match progress can be tested, but AFL++ CmpLog/Redqueen baselines are expected to be strong"
    if "numeric-margin" in categories:
        return "numeric-margin behavior is mostly a control unless native distance or branch feedback is uninformative"
    return f"{source} target requires TC audit before a benefit hypothesis is credible"


def lane_for(
    source: str,
    primary: str,
    secondary: str,
    specs: list[str],
    specs_validated: bool,
    disposition: str,
) -> str:
    if disposition in DEMOTE_DISPOSITIONS:
        return "control_or_negative"
    if source == "real_cve":
        if not hard_category(primary, secondary):
            return "real_cve_control_or_audit"
        if not specs:
            return "binding_spec_first"
        if specs and not specs_validated:
            return "binding_validation_first"
        return "real_cve_replacement"
    if specs_validated:
        return "short_triage_ready"
    if specs:
        return "binding_validation_first"
    if hard_category(primary, secondary):
        return "binding_spec_first"
    return "control_or_low_priority"


def suggested_triage(source: str, target_id: str, specs: list[str], specs_validated: bool) -> str:
    if specs and not specs_validated:
        if source == "real_cve":
            return (
                "build FORMTRIG-instrumented target/site map, compile the "
                "BindingSpec against native site ids, then run seed-readiness "
                "and binding-signal diagnosis"
            )
        return (
            "compile BindingSpec against the native site map, pass lift audit "
            "and binding-signal diagnosis, then run 10-30m FORMTRIG/baseline screen"
        )
    if source == "magma":
        if specs:
            return (
                "run 10-30m FORMTRIG seed-readiness/gate, then same-seed "
                f"AFL++ vanilla/CmpLog/Redqueen short baselines with "
                f"`scripts/run_magma_baselines.sh --target-id {target_id} "
                "--durations 600,1800 --jobs N`"
            )
        return (
            "draft BindingSpec from Magma canary sites, pass static/dynamic "
            f"binding audit, then run 10m FORMTRIG plus a 10m baseline screen "
            f"with `scripts/run_magma_baselines.sh --target-id {target_id} "
            "--durations 600 --jobs N`"
        )
    if specs:
        return (
            "run admissibility audit, ASAN replay, 10-30m FORMTRIG gate, and "
            "same-budget AFL++ family baselines"
        )
    return (
        "validate vulnerable build and PoC replay, write harness admissibility "
        "note, then create BindingSpec before fuzzing budget is spent"
    )


def status_for(
    source: str,
    primary: str,
    secondary: str,
    specs: list[str],
    specs_validated: bool,
    disposition: str,
    comparison_count: int,
    has_external_input: bool,
    has_commit: bool,
) -> tuple[str, list[str]]:
    blockers: list[str] = []
    if disposition in DEMOTE_DISPOSITIONS:
        blockers.append("existing comparison/admissibility evidence demotes this target")
        return "do_not_promote", blockers

    if source == "real_cve":
        if not has_external_input:
            blockers.append("no external PoC/input link recorded")
        if not has_commit:
            blockers.append("no vulnerable/fix commit link recorded")
        if not specs:
            blockers.append("no BindingSpec candidate exists yet")
        elif not specs_validated:
            blockers.append("BindingSpec candidate is not native-site-map validated")
        if not hard_category(primary, secondary):
            blockers.append("initial category is not binary/compound; treat as control unless audit shows D_T degeneration")
            return "needs_dt_degeneracy_audit", blockers
        if specs and not specs_validated:
            return "needs_binding_validation", blockers
        return ("candidate_after_replay_and_binding" if blockers else "ready_for_short_triage"), blockers

    if not specs:
        blockers.append("no BindingSpec candidate exists yet")
    elif not specs_validated:
        blockers.append("BindingSpec candidate is not native-site-map validated")
    if comparison_count == 0:
        blockers.append("no comparison package exists yet")
    if not hard_category(primary, secondary):
        blockers.append("category is likely direct-distance or CmpLog-friendly")
    if blockers:
        if specs and not specs_validated:
            return "needs_binding_validation", blockers
        return "needs_short_discovery", blockers
    return "ready_for_short_triage", blockers


def build_magma_rows(
    inventory_path: Path,
    binding_spec_dir: Path | None,
    dispositions: dict[str, dict[str, Any]],
    comparisons: Counter[str],
) -> list[dict[str, Any]]:
    payload = read_json(inventory_path)
    rows: list[dict[str, Any]] = []
    for record in payload.get("records", []):
        target_id = str(record.get("target_id") or "")
        if not target_id:
            continue
        primary = normalize_category(record.get("primary_tc_category"))
        secondary = normalize_category(record.get("secondary_tc_category"))
        disposition = str(dispositions.get(target_id, {}).get("disposition") or "")
        specs = binding_specs_for(target_id, binding_spec_dir)
        comparison_count = comparisons[target_id]
        status, blockers = status_for(
            "magma",
            primary,
            secondary,
            specs,
            binding_spec_validated(target_id),
            disposition,
            comparison_count,
            has_external_input=True,
            has_commit=True,
        )
        score = SOURCE_BASE_SCORE["magma"] + score_categories(primary, secondary)
        if boolish(record.get("ambiguous")):
            score += 4
        if record.get("classification_confidence") == "known_manifest":
            score += 7
        if record.get("build_status") == "pass":
            score += 8
        if specs:
            score += 12
        specs_validated = binding_spec_validated(target_id)
        if specs and not specs_validated:
            score -= 6
        if specs_validated:
            score += 10
        if comparison_count:
            score += min(comparison_count, 3)
        if disposition in DEMOTE_DISPOSITIONS:
            score -= 90
        rows.append(
            {
                "target_id": target_id,
                "source": "magma",
                "project": record.get("project"),
                "primary_category": primary,
                "secondary_category": secondary,
                "score": score,
                "lane": lane_for("magma", primary, secondary, specs, specs_validated, disposition),
                "status": status,
                "binding_spec": ",".join(specs),
                "binding_spec_validated": specs_validated,
                "existing_disposition": disposition,
                "benefit_hypothesis": benefit_hypothesis("magma", primary, secondary),
                "blockers": "; ".join(blockers),
                "next_action": next_action(status, "magma", target_id, primary, secondary, specs, specs_validated),
                "suggested_short_triage": suggested_triage("magma", target_id, specs, specs_validated),
                "source_evidence": str(inventory_path),
                "raw": {
                    "canary_expression": record.get("canary_expression"),
                    "program": record.get("program"),
                    "patch_path": record.get("patch_path"),
                    "comparison_count": comparison_count,
                },
            }
        )
    return rows


def build_cve_rows(
    inventory_path: Path,
    binding_spec_dir: Path | None,
    dispositions: dict[str, dict[str, Any]],
    comparisons: Counter[str],
) -> list[dict[str, Any]]:
    payload = read_json(inventory_path)
    rows: list[dict[str, Any]] = []
    for record in payload.get("records", []):
        target_id = str(record.get("candidate_id") or "")
        if not target_id:
            continue
        primary = normalize_category(record.get("initial_tc_category"))
        secondary = ""
        disposition = str(dispositions.get(target_id, {}).get("disposition") or "")
        specs = binding_specs_for(target_id, binding_spec_dir)
        specs_validated = binding_spec_validated(target_id)
        comparison_count = comparisons[target_id]
        has_external_input = bool(split_links(record.get("external_input_links")))
        has_commit = bool(split_links(record.get("commit_links")) or split_links(record.get("pull_links")))
        status, blockers = status_for(
            "real_cve",
            primary,
            secondary,
            specs,
            specs_validated,
            disposition,
            comparison_count,
            has_external_input=has_external_input,
            has_commit=has_commit,
        )
        score = SOURCE_BASE_SCORE["real_cve"] + score_categories(primary, secondary)
        if has_external_input:
            score += 12
        if has_commit:
            score += 10
        if specs:
            score += 14
        if specs and not specs_validated:
            score -= 6
        if specs_validated:
            score += 10
        if comparison_count:
            score += min(comparison_count, 3)
        if record.get("status") == "candidate_unvalidated":
            score -= 8
        if disposition in DEMOTE_DISPOSITIONS:
            score -= 95
        rows.append(
            {
                "target_id": target_id,
                "source": "real_cve",
                "project": record.get("project"),
                "primary_category": primary,
                "secondary_category": secondary,
                "score": score,
                "lane": lane_for("real_cve", primary, secondary, specs, specs_validated, disposition),
                "status": status,
                "binding_spec": ",".join(specs),
                "binding_spec_validated": specs_validated,
                "existing_disposition": disposition,
                "benefit_hypothesis": benefit_hypothesis("real_cve", primary, secondary),
                "blockers": "; ".join(blockers),
                "next_action": next_action(status, "real_cve", target_id, primary, secondary, specs, specs_validated),
                "suggested_short_triage": suggested_triage("real_cve", target_id, specs, specs_validated),
                "source_evidence": str(inventory_path),
                "raw": {
                    "bug_type": record.get("bug_type"),
                    "issue_url": record.get("issue_url"),
                    "title": record.get("title"),
                    "external_input_links": record.get("external_input_links"),
                    "commit_links": record.get("commit_links"),
                    "pull_links": record.get("pull_links"),
                    "comparison_count": comparison_count,
                },
            }
        )
    return rows


def next_action(
    status: str,
    source: str,
    target_id: str,
    primary: str,
    secondary: str,
    specs: list[str],
    specs_validated: bool,
) -> str:
    if status == "do_not_promote":
        return "keep as control or negative evidence; do not spend main long-run budget"
    if source == "real_cve":
        if not specs:
            return "validate vulnerable build/PoC replay, audit harness admissibility, then draft BindingSpec"
        if not specs_validated:
            return "validate BindingSpec against native site map and dynamic binding signal before short gate"
        return "run short FORMTRIG gate and same-budget AFL++ family baseline screen"
    if specs and not specs_validated:
        return "validate BindingSpec against native site map and binding-signal diagnosis before short gate"
    if specs_validated:
        if target_id == "PNG007":
            return "repair/spec-audit BindingSpec until accepted non-trigger D_F exists, then rerun short gate"
        return "run short FORMTRIG gate and same-seed AFL++ family baseline screen"
    if hard_category(primary, secondary):
        return "draft BindingSpec from TC root/producers, run binding audit, then short FORMTRIG/baseline triage"
    return "keep for control coverage unless a replay shows D_T degenerates to an uninformative binary signal"


def rank_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lane_rank = {
        "real_cve_replacement": 0,
        "short_triage_ready": 1,
        "binding_validation_first": 2,
        "binding_spec_first": 3,
        "real_cve_control_or_audit": 3,
        "control_or_low_priority": 4,
        "control_or_negative": 5,
    }
    rows = sorted(
        rows,
        key=lambda row: (
            lane_rank.get(str(row.get("lane")), 9),
            -int(row.get("score") or 0),
            str(row.get("target_id")),
        ),
    )
    for index, row in enumerate(rows, 1):
        row["rank"] = index
    return rows


def filtered_rows(rows: list[dict[str, Any]], include_controls: bool) -> list[dict[str, Any]]:
    if include_controls:
        return rows
    return [row for row in rows if row.get("lane") != "control_or_negative"]


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


def markdown_escape(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def write_markdown(path: Path, rows: list[dict[str, Any]], all_rows: list[dict[str, Any]], limit: int) -> None:
    top = rows[:limit]
    real_cve = [row for row in top if row.get("source") == "real_cve"]
    magma = [row for row in top if row.get("source") == "magma"]
    controls = [row for row in all_rows if row.get("lane") == "control_or_negative"]
    lines = [
        "# FORMTRIG Hard-Target Discovery Queue",
        "",
        "This queue is benefit-first. It ranks targets by whether they can",
        "plausibly expose a FORMTRIG advantage when terminal trigger feedback",
        "is binary or otherwise uninformative, then states the shortest next",
        "experiment needed to prove or discard that opportunity.",
        "",
        f"Top queued targets shown: `{len(top)}`.",
        f"Real-CVE replacements in top queue: `{len(real_cve)}`.",
        f"Magma candidates in top queue: `{len(magma)}`.",
        f"Demoted controls retained outside the main queue: `{len(controls)}`.",
        "",
        "## Top Queue",
        "",
        "| rank | target | source | project | category | score | lane | next action |",
        "| ---: | --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for row in top:
        category = row.get("primary_category") or ""
        if row.get("secondary_category"):
            category = f"{category}+{row.get('secondary_category')}"
        lines.append(
            "| {rank} | {target_id} | {source} | {project} | {category} | {score} | `{lane}` | {next_action} |".format(
                rank=row.get("rank", ""),
                target_id=markdown_escape(row.get("target_id")),
                source=markdown_escape(row.get("source")),
                project=markdown_escape(row.get("project")),
                category=markdown_escape(category),
                score=row.get("score", ""),
                lane=markdown_escape(row.get("lane")),
                next_action=markdown_escape(row.get("next_action")),
            )
        )

    lines.extend(
        [
            "",
            "## First Actions",
            "",
        ]
    )
    for row in top[:8]:
        lines.extend(
            [
                f"### {row.get('rank')}. {row.get('target_id')}",
                "",
                f"- Benefit hypothesis: {row.get('benefit_hypothesis')}",
                f"- Blockers: {row.get('blockers') or 'none recorded'}",
                f"- Short triage: {row.get('suggested_short_triage')}",
                "",
            ]
        )

    lines.extend(
        [
            "## Controls / Negative Evidence",
            "",
            "| target | disposition | next action |",
            "| --- | --- | --- |",
        ]
    )
    for row in controls:
        lines.append(
            "| {target_id} | `{disposition}` | {next_action} |".format(
                target_id=markdown_escape(row.get("target_id")),
                disposition=markdown_escape(row.get("existing_disposition")),
                next_action=markdown_escape(row.get("next_action")),
            )
        )

    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--magma-inventory", type=Path, default=Path("artifacts/magma_canary_inventory.json"))
    parser.add_argument("--cve-inventory", type=Path, default=Path("artifacts/cve_bench_candidate_audit.json"))
    parser.add_argument("--current-triage", type=Path, default=Path("artifacts/formtrig_native_readiness/hard_target_triage_20260616.json"))
    parser.add_argument("--comparison-root", type=Path, default=Path("artifacts/formtrig_native_readiness/comparisons"))
    parser.add_argument("--binding-spec-dir", type=Path, default=Path("artifacts/binding_specs"))
    parser.add_argument("--out-json", required=True, type=Path)
    parser.add_argument("--out-csv", required=True, type=Path)
    parser.add_argument("--out-md", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--include-controls", action="store_true")
    return parser.parse_args()


def disposition_only_rows(dispositions: dict[str, dict[str, Any]], existing_target_ids: set[str], source_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for target_id, triage_row in sorted(dispositions.items()):
        if target_id in existing_target_ids:
            continue
        disposition = str(triage_row.get("disposition") or "")
        if disposition not in DEMOTE_DISPOSITIONS:
            continue
        rows.append(
            {
                "target_id": target_id,
                "source": "existing_evidence",
                "project": "",
                "primary_category": "",
                "secondary_category": "",
                "score": -99,
                "lane": "control_or_negative",
                "status": "do_not_promote",
                "binding_spec": "",
                "existing_disposition": disposition,
                "benefit_hypothesis": "current evidence does not support a main hard-target benefit claim",
                "blockers": str(triage_row.get("blocked_claims") or ""),
                "next_action": "keep as control or negative evidence; do not spend main long-run budget",
                "suggested_short_triage": "none for main queue",
                "source_evidence": str(source_path),
                "raw": {"triage_row": triage_row},
            }
        )
    return rows


def main() -> int:
    args = parse_args()
    dispositions = existing_dispositions(args.current_triage)
    comparisons = comparison_targets(args.comparison_root)
    rows: list[dict[str, Any]] = []
    if args.magma_inventory.exists():
        rows.extend(build_magma_rows(args.magma_inventory, args.binding_spec_dir, dispositions, comparisons))
    if args.cve_inventory.exists():
        rows.extend(build_cve_rows(args.cve_inventory, args.binding_spec_dir, dispositions, comparisons))
    rows.extend(disposition_only_rows(dispositions, {str(row.get("target_id")) for row in rows}, args.current_triage))

    ranked = rank_rows(rows)
    selected = filtered_rows(ranked, args.include_controls)
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inputs": {
            "magma_inventory": str(args.magma_inventory),
            "cve_inventory": str(args.cve_inventory),
            "current_triage": str(args.current_triage),
            "comparison_root": str(args.comparison_root),
            "binding_spec_dir": str(args.binding_spec_dir),
        },
        "row_count": len(ranked),
        "selected_count": len(selected),
        "limit": args.limit,
        "top_targets": selected[: args.limit],
        "all_targets": ranked,
    }
    write_json(args.out_json, payload)
    write_csv(args.out_csv, selected[: args.limit])
    write_markdown(args.out_md, selected, ranked, args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
