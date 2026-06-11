#!/usr/bin/env python3
"""Run FORMTRIG preflight-v2 semantic hard gate only."""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import tarfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    "T1_NUMERIC_ACTIONABLE",
    "T2_EQUALITY_DIRECT_ANYOF",
    "T3_EQUALITY_TRANSFORMED",
    "T4_BINARY_NULL_LIFT",
    "T5_GUARDED_BINARY",
    "T6_SAME_OBJECT_LIFECYCLE",
]
BASELINES = ["native_tc_dgf", "native_tc_dgf_typedmut", "formtrig"]
MODES = ["postreach", "e2e"]
MUTATION_ACCEPT = {
    "triggered",
    "native-distance improvement",
    "lifted-feature improvement",
    "root-aligned state transition",
    "lifecycle-prefix improvement",
    "influence-confidence improvement",
}
VALID_REJECT = {
    "not_reached",
    "not_replay_stable",
    "not_root_or_event_aligned",
    "coverage_only",
    "regressed_higher_priority_atom",
    "no_tc_rooted_dominance",
    "insufficient_object_identity",
    "blocked_by_guard",
    "dominated_by_existing_frontier",
    "budget_exhausted",
    "not_executed",
    "precondition_not_satisfied",
}
FORBIDDEN_TYPED_MUTATORS = {
    "boundary write",
    "operand replacement",
    "optional-region deletion",
    "guard-field perturbation",
    "error-path induction",
    "initialization-bypass mutation",
    "reset/cleanup-path mutation",
    "event insertion",
    "object-identity alignment",
    "event deletion",
    "event duplication",
    "event reordering",
    "phase-preserving mutation",
    "arithmetic perturbation",
    "numeric byte increment",
    "endian variants",
    "dictionary insertion",
    "token replacement",
    "repair hook",
}
EXPECTED_FORMTRIG_TRIGGER = {
    "T1_NUMERIC_ACTIONABLE": True,
    "T2_EQUALITY_DIRECT_ANYOF": True,
    "T3_EQUALITY_TRANSFORMED": False,
    "T4_BINARY_NULL_LIFT": True,
    "T5_GUARDED_BINARY": True,
    "T6_SAME_OBJECT_LIFECYCLE": True,
}
NATIVE_EXPECTED_NONTRIGGER = {
    "T3_EQUALITY_TRANSFORMED",
    "T4_BINARY_NULL_LIFT",
    "T5_GUARDED_BINARY",
    "T6_SAME_OBJECT_LIFECYCLE",
}


def run_cmd(cmd: list[str], cwd: Path = ROOT) -> dict[str, object]:
    start = time.time()
    proc = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "elapsed_s": time.time() - start,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def ensure_fresh_v4() -> list[dict[str, object]]:
    return [
        run_cmd(["gcc", "-O2", "-Wall", "-Wextra", "-Werror", "-o", "benchmarks/fresh_v4_cases/fresh_v4_cases", "benchmarks/fresh_v4_cases/fresh_v4_cases.c"]),
        run_cmd(["python3", "benchmarks/fresh_v4_cases/build_seedbanks.py"]),
    ]


def write_baseline_matrix() -> None:
    generic = "generic byte perturbation;generic byte increment;generic byte decrement;generic token insertion"
    typed = ";".join(sorted(FORBIDDEN_TYPED_MUTATORS))
    rows = [
        {
            "baseline": "native_tc_dgf",
            "uses_native_DT": "true",
            "uses_lifted_DF": "false",
            "uses_typed_mutators": "false",
            "uses_TC_atoms": "false",
            "uses_producer_context": "false",
            "uses_lifecycle_context": "false",
            "allowed_mutators": generic,
            "forbidden_mutators": typed,
        },
        {
            "baseline": "native_tc_dgf_typedmut",
            "uses_native_DT": "true",
            "uses_lifted_DF": "false",
            "uses_typed_mutators": "true",
            "uses_TC_atoms": "true",
            "uses_producer_context": "false",
            "uses_lifecycle_context": "false",
            "allowed_mutators": "native DT scheduling plus typed mutators",
            "forbidden_mutators": "lifted features;producer context;lifecycle context",
        },
        {
            "baseline": "formtrig",
            "uses_native_DT": "true",
            "uses_lifted_DF": "true",
            "uses_typed_mutators": "true",
            "uses_TC_atoms": "true",
            "uses_producer_context": "true",
            "uses_lifecycle_context": "true",
            "allowed_mutators": "registry typed mutators plus generic fallback",
            "forbidden_mutators": "",
        },
    ]
    write_csv(ROOT / "artifacts" / "baseline_matrix.csv", rows)


def inventory() -> dict[str, dict[str, str]]:
    return {row["target_id"]: row for row in read_csv(ROOT / "artifacts" / "fresh_v4_inventory.csv")}


def run_one(target_id: str, baseline: str, mode: str, out_dir: Path, inv: dict[str, dict[str, str]]) -> dict[str, object]:
    wrapper = ROOT / "bin" / ("formtrig_postreach" if mode == "postreach" else "formtrig_e2e")
    metadata = ROOT / "artifacts" / "rnt_corpus" / target_id / "metadata.csv"
    cmd = [
        str(wrapper),
        "--target-id", target_id,
        "--inventory", "artifacts/fresh_v4_inventory.csv",
        "--metadata-csv", str(metadata),
        "--out-dir", str(out_dir),
        "--target-cmd", inv[target_id]["run_command"],
        "--per-exec-timeout", "1",
        "--baseline", baseline,
        "--calibration-mutations-per-seed", "8",
        "--max-seed-records", "10",
        "--max-mutation-proposals-per-seed", "8",
        "--max-total-mutations", "96",
    ]
    if mode == "postreach":
        cmd.append("--execute-mutations")
    result = run_cmd(cmd)
    write_json(out_dir / "command.json", result)
    return result


def validate_run(run_dir: Path, target_id: str, baseline: str, mode: str, command: dict[str, object]) -> tuple[list[str], list[str], list[str]]:
    semantic: list[str] = []
    schema: list[str] = []
    repro: list[str] = []
    required = [
        "logs/atom_plans_coarse.json",
        "logs/atom_plans_final.json",
        "logs/progress_decisions.jsonl",
        "logs/progress_records.jsonl",
        "logs/mutation_records.jsonl",
        "logs/frontier_snapshots.jsonl",
        "results/diagnostics/signal_health_by_atom.csv",
        "results/diagnostics/calibration_edges.jsonl",
    ]
    for rel in required:
        if not (run_dir / rel).exists():
            schema.append(f"missing:{run_dir / rel}")
    if mode == "e2e":
        if "--dry-run" in command.get("cmd", []):
            semantic.append(f"e2e_used_dry_run:{target_id}:{baseline}")
        for rel in ["logs/base_queue_stats.json", "logs/trigger_progress_frontier_stats.json"]:
            if not (run_dir / rel).exists():
                schema.append(f"missing_e2e_stats:{run_dir / rel}")

    health = read_csv(run_dir / "results" / "diagnostics" / "signal_health_by_atom.csv")
    if target_id == "T1_NUMERIC_ACTIONABLE":
        if not health or any(row.get("native_status") != "actionable" for row in health):
            semantic.append(f"numeric_actionable_not_actionable:{run_dir}")
    if target_id == "T4_BINARY_NULL_LIFT":
        if not health or any(row.get("native_status") != "degenerated" for row in health):
            semantic.append(f"binary_null_lift_not_degenerated:{run_dir}")
        if not any("native_DT_not_discriminative" in row.get("failed_checks", "") for row in health):
            semantic.append(f"binary_null_lift_missing_discriminative_failure:{run_dir}")
    if target_id == "T6_SAME_OBJECT_LIFECYCLE":
        if not health or any(row.get("native_status") != "degenerated" for row in health):
            semantic.append(f"lifecycle_not_degenerated:{run_dir}")
        if not any("native_DT_not_discriminative" in row.get("failed_checks", "") or "object" in row.get("failed_checks", "") for row in health):
            semantic.append(f"lifecycle_missing_expected_failure:{run_dir}")

    calib_count = len(jsonl(run_dir / "results" / "diagnostics" / "calibration_edges.jsonl"))
    insuff = read_csv(run_dir / "results" / "diagnostics" / "insufficient_edges.csv")
    if calib_count < 32 and not insuff:
        semantic.append(f"insufficient_calibration_edges_without_reason:{run_dir}:{calib_count}")
    if target_id == "T1_NUMERIC_ACTIONABLE" and calib_count < 32:
        semantic.append(f"numeric_actionable_insufficient_edges:{run_dir}:{calib_count}")

    mutation_rows = jsonl(run_dir / "logs" / "mutation_records.jsonl")
    if mode == "e2e" and len(mutation_rows) == 0:
        semantic.append(f"e2e_no_mutation_records:{target_id}:{baseline}")
    for row in mutation_rows:
        for key in ["operator_family", "precondition_satisfied", "effect", "decision_reason"]:
            if key not in row:
                schema.append(f"mutation_missing_{key}:{run_dir}")
        if baseline == "native_tc_dgf" and row.get("operator_name") in FORBIDDEN_TYPED_MUTATORS:
            semantic.append(f"native_tc_dgf_used_typed_mutator:{target_id}:{row.get('operator_name')}")

    decisions = jsonl(run_dir / "logs" / "progress_decisions.jsonl")
    if mode == "e2e" and not any(row.get("event") == "mutation_progress_decision" for row in decisions):
        semantic.append(f"e2e_missing_mutation_progress_decision:{target_id}:{baseline}")
    for row in decisions:
        accepted = bool(row.get("accepted"))
        reason = str(row.get("reason", ""))
        event = str(row.get("event", ""))
        if accepted and event in {"seed_import_progress_decision", "dynamic_rnt_progress_decision"}:
            if reason != "initial_frontier_seed":
                semantic.append(f"initial_seed_used_mutation_reason:{run_dir}:{reason}")
        if accepted and event == "mutation_progress_decision":
            if reason not in MUTATION_ACCEPT:
                semantic.append(f"invalid_mutation_accept_reason:{run_dir}:{reason}")
            if reason == "initial_frontier_seed":
                semantic.append(f"mutation_used_initial_reason:{run_dir}")
        if not accepted and reason and reason not in VALID_REJECT:
            schema.append(f"invalid_reject_reason:{run_dir}:{reason}")
        if accepted and reason == "triggered":
            if not row.get("vector"):
                semantic.append(f"trigger_vector_empty:{run_dir}:{row.get('seed_id')}")
            replay_count = int(row.get("details", {}).get("replay_count", 0))
            if replay_count < 2:
                semantic.append(f"trigger_replay_count_lt_2:{run_dir}:{row.get('seed_id')}")

    if target_id == "T2_EQUALITY_DIRECT_ANYOF":
        branches = {
            record.get("global_progress", {}).get("selected_branch", "")
            for record in jsonl(run_dir / "logs" / "progress_records.jsonl")
            if record.get("event") in {"seed_import_progress_record", "dynamic_rnt_progress_record"}
        }
        branches.discard("")
        if len(branches) < 2:
            semantic.append(f"anyof_frontier_missing_active_branch:{run_dir}:{sorted(branches)}")

    if target_id == "T5_GUARDED_BINARY":
        blocked_seen = False
        false_blocked = False
        for record in jsonl(run_dir / "logs" / "progress_records.jsonl"):
            for atom in record.get("atoms", []):
                root_state = str(atom.get("root_state", ""))
                obs = atom.get("root_events", [])
                if "blocked_by_guard=1" in root_state and "binary-state-null" == atom.get("atom_type"):
                    status = record.get("global_progress", {}).get("full_progress_vector", {}).get("atom_observations", {}).get(atom.get("atom_id"), {}).get("status")
                    blocked_seen = blocked_seen or status == "BLOCKED_BY_GUARD"
                    false_blocked = false_blocked or status == "OBSERVED_FALSE"
        if not blocked_seen:
            semantic.append(f"guard_blocked_status_not_seen:{run_dir}")
        if false_blocked:
            semantic.append(f"guard_blocked_marked_false:{run_dir}")

    if target_id == "T6_SAME_OBJECT_LIFECYCLE":
        if not any(row.get("reason") == "insufficient_object_identity" for row in decisions):
            semantic.append(f"lifecycle_missing_wrong_object_rejection:{run_dir}")

    status_path = run_dir / "status.json"
    if baseline == "native_tc_dgf" and target_id in NATIVE_EXPECTED_NONTRIGGER and status_path.exists():
        status = json.loads(status_path.read_text())
        if status.get("trigger_success"):
            semantic.append(f"native_tc_dgf_unexpected_trigger:{target_id}:{mode}")
    return semantic, schema, repro


def validate_global_artifacts() -> tuple[list[str], list[str], list[str]]:
    semantic: list[str] = []
    schema: list[str] = []
    repro: list[str] = []
    for target_id in TARGETS:
        for rel in [
            ROOT / "artifacts" / "tcir" / f"{target_id}.json",
            ROOT / "artifacts" / "atoms" / f"{target_id}.json",
            ROOT / "artifacts" / "trigger_graphs" / f"{target_id}.json",
        ]:
            if not rel.exists():
                schema.append(f"missing_global_artifact:{rel}")
        rows = read_csv(ROOT / "artifacts" / "rnt_corpus" / target_id / "metadata.csv")
        if len([row for row in rows if row.get("reached_R") == "1" and row.get("triggered_T") == "0"]) < 10:
            repro.append(f"target_missing_10_rnt:{target_id}")
    t6 = ROOT / "artifacts" / "tcir" / "T6_SAME_OBJECT_LIFECYCLE.json"
    if t6.exists():
        payload = json.loads(t6.read_text())
        same_edges = [edge for edge in payload.get("edges", []) if edge.get("edge_type") == "SAME_OBJECT"]
        if not same_edges:
            semantic.append("same_object_edges_missing:T6")
        if same_edges and all(edge.get("src") == edge.get("dst") for edge in same_edges):
            semantic.append("same_object_edges_self_loop_only:T6")
    matrix = read_csv(ROOT / "artifacts" / "baseline_matrix.csv")
    native = next((row for row in matrix if row.get("baseline") == "native_tc_dgf"), {})
    expected = {
        "uses_native_DT": "true",
        "uses_lifted_DF": "false",
        "uses_typed_mutators": "false",
        "uses_producer_context": "false",
        "uses_lifecycle_context": "false",
    }
    for key, value in expected.items():
        if native.get(key) != value:
            semantic.append(f"baseline_matrix_native_bad:{key}:{native.get(key)}")
    return semantic, schema, repro


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    if src.exists():
        shutil.copytree(src, dst)


def aggregate_package(batch_dir: Path, checks: dict[str, object], run_results: list[dict[str, object]]) -> Path:
    package_root = batch_dir / "package_root"
    if package_root.exists():
        shutil.rmtree(package_root)
    package_root.mkdir(parents=True)
    copy_tree(ROOT / "benchmarks" / "fresh_v4_cases", package_root / "benchmarks" / "fresh_v4_cases")
    copy_tree(ROOT / "bin", package_root / "bin")
    copy_tree(ROOT / "configs", package_root / "configs")
    copy_tree(ROOT / "tests", package_root / "tests")
    copy_tree(ROOT / "scripts", package_root / "scripts")
    (package_root / "tools").mkdir()
    for name in ["__init__.py", "formtrig_algorithm_core.py", "formtrig_modes.py", "run_formtrig_preflight_v2.py"]:
        shutil.copy2(ROOT / "tools" / name, package_root / "tools" / name)
    (package_root / "artifacts").mkdir(exist_ok=True)
    for name in ["fresh_v4_inventory.csv", "baseline_matrix.csv"]:
        shutil.copy2(ROOT / "artifacts" / name, package_root / "artifacts" / name)
    for target in TARGETS:
        copy_tree(ROOT / "artifacts" / "rnt_corpus" / target, package_root / "artifacts" / "rnt_corpus" / target)
        for family in ["tcir", "atoms", "trigger_graphs"]:
            src = ROOT / "artifacts" / family / f"{target}.json"
            dst = package_root / "artifacts" / family / f"{target}.json"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    if (ROOT / "artifacts" / "registry_dump.json").exists():
        shutil.copy2(ROOT / "artifacts" / "registry_dump.json", package_root / "artifacts" / "registry_dump.json")
    logs_root = package_root / "logs"
    results_root = package_root / "results"
    diag_rows: list[dict[str, object]] = []
    target_rows: list[dict[str, object]] = []
    calib_rows: list[dict[str, object]] = []
    for run_dir in sorted((batch_dir / "runs").glob("*/*/*")):
        target, baseline, mode = run_dir.parts[-3:]
        copy_tree(run_dir / "logs", logs_root / mode / target / baseline)
        copy_tree(run_dir / "results", results_root / mode / target / baseline)
        for row in read_csv(run_dir / "results" / "diagnostics" / "signal_health_by_atom.csv"):
            row.update({"target_id": target, "baseline": baseline, "mode": mode})
            diag_rows.append(row)
        for row in read_csv(run_dir / "results" / "diagnostics" / "signal_health_by_target.csv"):
            row.update({"target_id": target, "baseline": baseline, "mode": mode})
            target_rows.append(row)
        for row in jsonl(run_dir / "results" / "diagnostics" / "calibration_edges.jsonl"):
            row.update({"target_id": target, "baseline": baseline, "mode": mode})
            calib_rows.append(row)
    write_csv(results_root / "diagnostics" / "signal_health_by_atom.csv", diag_rows)
    write_csv(results_root / "diagnostics" / "signal_health_by_target.csv", target_rows)
    (results_root / "diagnostics" / "calibration_edges.jsonl").parent.mkdir(parents=True, exist_ok=True)
    with (results_root / "diagnostics" / "calibration_edges.jsonl").open("w") as f:
        for row in calib_rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    write_json(package_root / "preflight_v2_checks.json", checks)
    commit = run_cmd(["git", "rev-parse", "HEAD"])
    env = run_cmd(["bash", "-lc", "uname -a; python3 --version; gcc --version | head -n 1"])
    readme = [
        "# FORMTRIG Preflight-v2 Package",
        "",
        "## Exact Commands",
        "- `bash scripts/reproduce_preflight_v2.sh`",
        *[f"- `{' '.join(map(str, item['cmd']))}`" for item in run_results if item.get("cmd")],
        "",
        "## Environment",
        "```text",
        str(env.get("stdout", "")).strip(),
        "```",
        "",
        "## Commit Hash",
        str(commit.get("stdout", "")).strip() if commit.get("returncode") == 0 else "unavailable",
        "",
        "## Target List",
        *[f"- {target}" for target in TARGETS],
        "",
        "## Baseline List",
        *[f"- {baseline}" for baseline in BASELINES],
        "",
        "## Mode List",
        *[f"- {mode}" for mode in MODES],
        "",
        "## Expected Trigger Matrix",
        *[f"- {target}: FORMTRIG expected trigger={str(value).lower()}" for target, value in EXPECTED_FORMTRIG_TRIGGER.items()],
        "",
        "## Native-TC-DGF Expected Non-Trigger Targets",
        *[f"- {target}" for target in sorted(NATIVE_EXPECTED_NONTRIGGER)],
        "",
        "## Known Limitations",
        "- This package is a local semantic preflight and does not include full Magma/CVE/ablation/paper-data experiments.",
        "- The fresh_v4 targets are synthetic hard-gate cases for algorithm correctness checks.",
        "",
    ]
    (package_root / "README.md").write_text("\n".join(readme))
    tar_path = ROOT / "preflight_v2_package.tar.gz"
    if tar_path.exists():
        tar_path.unlink()
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(package_root, arcname="preflight_v2_package")
    return tar_path


def validate_package(tar_path: Path) -> list[str]:
    required = [
        "preflight_v2_package/benchmarks/fresh_v4_cases/fresh_v4_cases.c",
        "preflight_v2_package/benchmarks/fresh_v4_cases/build_seedbanks.py",
        "preflight_v2_package/artifacts/fresh_v4_inventory.csv",
        "preflight_v2_package/artifacts/baseline_matrix.csv",
        "preflight_v2_package/bin/formtrig_postreach",
        "preflight_v2_package/bin/formtrig_e2e",
        "preflight_v2_package/scripts/reproduce_preflight_v2.sh",
        "preflight_v2_package/tools/formtrig_modes.py",
        "preflight_v2_package/tests/test_tcir_semantics.py",
        "preflight_v2_package/preflight_v2_checks.json",
        "preflight_v2_package/README.md",
    ]
    failures: list[str] = []
    with tarfile.open(tar_path) as tf:
        names = set(tf.getnames())
    for name in required:
        if name not in names:
            failures.append(f"package_missing:{name}")
    for target in TARGETS:
        for suffix in ["metadata.csv", "seeds"]:
            name = f"preflight_v2_package/artifacts/rnt_corpus/{target}/{suffix}"
            if not any(item == name or item.startswith(name + "/") for item in names):
                failures.append(f"package_missing:{name}")
    return failures


def main() -> int:
    batch_id = time.strftime("formtrig_preflight_v2_%Y%m%dT%H%M%SZ", time.gmtime())
    batch_dir = ROOT / "results" / "preflight_v2" / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    run_results = ensure_fresh_v4()
    write_baseline_matrix()
    inv = inventory()
    semantic: list[str] = []
    schema: list[str] = []
    repro: list[str] = []
    for setup in run_results:
        if setup["returncode"] != 0:
            repro.append(f"setup_failed:{setup['cmd']}:{setup['stderr']}")
    for target_id in TARGETS:
        for baseline in BASELINES:
            for mode in MODES:
                run_dir = batch_dir / "runs" / target_id / baseline / mode
                result = run_one(target_id, baseline, mode, run_dir, inv)
                run_results.append(result)
                if result["returncode"] != 0:
                    repro.append(f"run_failed:{target_id}:{baseline}:{mode}:{result['stderr']}")
                s, c, r = validate_run(run_dir, target_id, baseline, mode, result)
                semantic.extend(s)
                schema.extend(c)
                repro.extend(r)
    s, c, r = validate_global_artifacts()
    semantic.extend(s)
    schema.extend(c)
    repro.extend(r)
    checks = {
        "status": "pass" if not semantic and not schema and not repro else "fail",
        "semantic_failures": semantic,
        "schema_failures": schema,
        "reproducibility_failures": repro,
    }
    write_json(ROOT / "preflight_v2_checks.json", checks)
    tar_path = aggregate_package(batch_dir, checks, run_results)
    package_failures = validate_package(tar_path)
    if package_failures:
        checks["status"] = "fail"
        checks["reproducibility_failures"] = list(checks["reproducibility_failures"]) + package_failures
        write_json(ROOT / "preflight_v2_checks.json", checks)
        write_json(batch_dir / "package_root" / "preflight_v2_checks.json", checks)
        tar_path = aggregate_package(batch_dir, checks, run_results)
    summary = {"batch_dir": str(batch_dir), "package": str(tar_path), **checks}
    write_json(batch_dir / "preflight_v2_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if checks["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
