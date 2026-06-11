#!/usr/bin/env python3
"""Run FORMTRIG v3 preflight only; no full-scale experiments."""

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
    "FRESH_NUMERIC_MARGIN",
    "FRESH_ANY_OF",
    "FRESH_GUARDED_NUMERIC_BINARY",
    "FRESH_SAME_OBJECT_LIFECYCLE",
]
BASELINES = ["native_tc_dgf", "formtrig"]
MODES = ["postreach", "e2e"]
VALID_ACCEPT = {
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


def read_inventory() -> dict[str, dict[str, str]]:
    path = ROOT / "artifacts" / "fresh_v3_inventory.csv"
    with path.open(newline="") as f:
        return {row["target_id"]: row for row in csv.DictReader(f)}


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


def ensure_fresh_targets() -> list[dict[str, object]]:
    return [
        run_cmd(["gcc", "-O2", "-Wall", "-Wextra", "-Werror", "-o", "benchmarks/fresh_v3_cases/fresh_v3_cases", "benchmarks/fresh_v3_cases/fresh_v3_cases.c"]),
        run_cmd(["python3", "benchmarks/fresh_v3_cases/build_seedbanks.py"]),
    ]


def run_one(target_id: str, baseline: str, mode: str, out_dir: Path, inventory: dict[str, dict[str, str]]) -> dict[str, object]:
    row = inventory[target_id]
    target_cmd = row["run_command"]
    metadata = ROOT / "artifacts" / "rnt_corpus" / target_id / "metadata.csv"
    wrapper = ROOT / "bin" / ("formtrig_postreach" if mode == "postreach" else "formtrig_e2e")
    cmd = [
        str(wrapper),
        "--target-id", target_id,
        "--inventory", "artifacts/fresh_v3_inventory.csv",
        "--metadata-csv", str(metadata),
        "--out-dir", str(out_dir),
        "--target-cmd", target_cmd,
        "--per-exec-timeout", "1",
        "--baseline", baseline,
        "--calibration-mutations-per-seed", "4",
    ]
    if mode == "postreach":
        cmd.extend(["--execute-mutations", "--max-seed-records", "5", "--max-mutation-proposals-per-seed", "6", "--max-total-mutations", "40"])
    else:
        cmd.append("--dry-run")
    result = run_cmd(cmd)
    (out_dir / "command.json").parent.mkdir(parents=True, exist_ok=True)
    (out_dir / "command.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def validate_run(run_dir: Path) -> list[str]:
    failures: list[str] = []
    required = [
        "logs/atom_plans_coarse.json",
        "logs/atom_plans_final.json",
        "results/diagnostics/signal_health_by_atom.csv",
        "logs/progress_records.jsonl",
        "logs/mutation_records.jsonl",
        "logs/progress_decisions.jsonl",
        "logs/frontier_snapshots.jsonl",
    ]
    for rel in required:
        if not (run_dir / rel).exists():
            failures.append(f"missing:{run_dir / rel}")

    for row in jsonl(run_dir / "logs" / "progress_decisions.jsonl"):
        accepted = bool(row.get("accepted"))
        reason = str(row.get("reason", ""))
        if accepted:
            if reason not in VALID_ACCEPT:
                failures.append(f"invalid_accept_reason:{run_dir}:{reason}")
            if reason != "triggered" and not bool(row.get("replay_verifiable")):
                failures.append(f"accepted_not_replay_stable:{run_dir}:{row.get('seed_id')}")
            if reason == "coverage_only":
                failures.append(f"coverage_only_accepted:{run_dir}:{row.get('seed_id')}")
        else:
            if reason and reason not in VALID_REJECT:
                failures.append(f"invalid_reject_reason:{run_dir}:{reason}")

    trigger_decisions = [row for row in jsonl(run_dir / "logs" / "progress_decisions.jsonl") if row.get("accepted") and row.get("reason") == "triggered"]
    for row in trigger_decisions:
        evidence = run_dir / "trigger_evidence"
        if not evidence.exists() or not list(evidence.glob("*/replays.jsonl")):
            failures.append(f"missing_trigger_evidence:{run_dir}:{row.get('seed_id')}")
        else:
            for replay_log in evidence.glob("*/replays.jsonl"):
                if len(jsonl(replay_log)) < 2:
                    failures.append(f"trigger_replay_count_lt_2:{replay_log}")

    health_path = run_dir / "results" / "diagnostics" / "signal_health_by_atom.csv"
    if health_path.exists():
        with health_path.open(newline="") as f:
            for row in csv.DictReader(f):
                if not row.get("native_status"):
                    failures.append(f"missing_native_status:{run_dir}:{row.get('atom_id')}")
                if row.get("native_status") != "actionable" and not row.get("failed_checks"):
                    failures.append(f"missing_failed_checks:{run_dir}:{row.get('atom_id')}")

    final_plans = run_dir / "logs" / "atom_plans_final.json"
    if final_plans.exists():
        payload = json.loads(final_plans.read_text())
        for plan in payload.get("plans", []):
            if plan.get("use_lifted_features"):
                features = plan.get("graph_features") or []
                if not features:
                    failures.append(f"lifted_plan_missing_graph_features:{run_dir}:{plan.get('atom_id')}")
                for feature in features:
                    if feature.get("feature") not in {
                        "root variable/event",
                        "producer context",
                        "guard context",
                        "use context",
                        "sequence/lifecycle node",
                        "influence range",
                    }:
                        failures.append(f"invalid_graph_feature:{run_dir}:{feature}")

    for row in jsonl(run_dir / "logs" / "mutation_records.jsonl"):
        if "precondition" not in row or row.get("precondition") in ({}, None):
            failures.append(f"mutation_missing_precondition:{run_dir}")
        if row.get("executed") and not row.get("effect"):
            failures.append(f"mutation_missing_replay_outcome:{run_dir}")

    calib = run_dir / "results" / "diagnostics" / "calibration_edges.jsonl"
    insuff = run_dir / "results" / "diagnostics" / "insufficient_edges.csv"
    if not calib.exists():
        failures.append(f"missing_calibration_edges:{run_dir}")
    elif not calib.read_text().strip() and (not insuff.exists() or not insuff.read_text().strip()):
        failures.append(f"no_calibration_edges_or_infeasibility:{run_dir}")
    return failures


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    if src.exists():
        shutil.copytree(src, dst)


def aggregate_and_package(batch_dir: Path, run_results: list[dict[str, object]], failures: list[str]) -> Path:
    package_root = batch_dir / "package_root"
    if package_root.exists():
        shutil.rmtree(package_root)
    package_root.mkdir(parents=True)
    copy_tree(ROOT / "artifacts" / "tcir", package_root / "artifacts" / "tcir")
    copy_tree(ROOT / "artifacts" / "atoms", package_root / "artifacts" / "atoms")
    copy_tree(ROOT / "artifacts" / "trigger_graphs", package_root / "artifacts" / "trigger_graphs")
    if (ROOT / "artifacts" / "registry_dump.json").exists():
        shutil.copy2(ROOT / "artifacts" / "registry_dump.json", package_root / "artifacts" / "registry_dump.json")
    copy_tree(ROOT / "configs", package_root / "configs")
    (package_root / "scripts").mkdir()
    shutil.copy2(ROOT / "tools" / "run_formtrig_preflight.py", package_root / "scripts" / "run_formtrig_preflight.py")

    logs_root = package_root / "logs"
    results_root = package_root / "results"
    diagnostics_rows = []
    target_health_rows = []
    calibration_rows = []
    insufficient_rows = []
    for run_dir in sorted((batch_dir / "runs").glob("*/*/*")):
        target, baseline, mode = run_dir.parts[-3:]
        dst_logs = logs_root / mode / target / baseline
        copy_tree(run_dir / "logs", dst_logs)
        copy_tree(run_dir / "results", results_root / mode / target / baseline)
        health = run_dir / "results" / "diagnostics" / "signal_health_by_atom.csv"
        if health.exists():
            with health.open(newline="") as f:
                for row in csv.DictReader(f):
                    row.update({"mode": mode, "baseline": baseline})
                    diagnostics_rows.append(row)
        target_health = run_dir / "results" / "diagnostics" / "signal_health_by_target.csv"
        if target_health.exists():
            with target_health.open(newline="") as f:
                for row in csv.DictReader(f):
                    row.update({"mode": mode, "baseline": baseline})
                    target_health_rows.append(row)
        calib = run_dir / "results" / "diagnostics" / "calibration_edges.jsonl"
        if calib.exists():
            for line in calib.read_text().splitlines():
                if line.strip():
                    row = json.loads(line)
                    row.update({"mode": mode, "baseline": baseline})
                    calibration_rows.append(row)
        insuff = run_dir / "results" / "diagnostics" / "insufficient_edges.csv"
        if insuff.exists() and insuff.read_text().strip():
            with insuff.open(newline="") as f:
                for row in csv.DictReader(f):
                    row.update({"mode": mode, "baseline": baseline})
                    insufficient_rows.append(row)
    diag_dir = results_root / "diagnostics"
    diag_dir.mkdir(parents=True, exist_ok=True)
    if diagnostics_rows:
        with (diag_dir / "signal_health_by_atom.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(diagnostics_rows[0].keys()))
            writer.writeheader()
            writer.writerows(diagnostics_rows)
    if target_health_rows:
        with (diag_dir / "signal_health_by_target.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(target_health_rows[0].keys()))
            writer.writeheader()
            writer.writerows(target_health_rows)
    (diag_dir / "calibration_edges.jsonl").write_text("")
    for row in calibration_rows:
        with (diag_dir / "calibration_edges.jsonl").open("a") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    if insufficient_rows:
        with (diag_dir / "insufficient_edges.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(insufficient_rows[0].keys()))
            writer.writeheader()
            writer.writerows(insufficient_rows)
    else:
        (diag_dir / "insufficient_edges.csv").write_text("target_id,reason,mode,baseline\n")
    (package_root / "preflight_checks.json").write_text(json.dumps({"failures": failures, "runs": run_results}, indent=2, sort_keys=True) + "\n")
    commit = run_cmd(["git", "rev-parse", "HEAD"])
    if commit["returncode"] == 0:
        commit_text = str(commit["stdout"]).strip()
    else:
        stderr = str(commit["stderr"]).strip()
        commit_text = f"unavailable ({stderr or 'git rev-parse HEAD failed'})"
    env = run_cmd(["bash", "-lc", "uname -a; python3 --version; gcc --version | head -n 1"])
    readme = [
        "# FORMTRIG v3 Preflight Package",
        "",
        "## Target List",
        *[f"- {target}" for target in TARGETS],
        "",
        "## Baselines",
        *[f"- {baseline}" for baseline in BASELINES],
        "",
        "## Modes",
        *[f"- {mode}" for mode in MODES],
        "",
        "## Commands Run",
        *[f"- `{' '.join(map(str, item['cmd']))}`" for item in run_results if "cmd" in item],
        "",
        "## Commit Hash",
        commit_text,
        "",
        "## Environment",
        "```text",
        str(env["stdout"]).strip(),
        "```",
        "",
        "## Checks Passed",
        "yes" if not failures else "no",
        "",
        "## Checks Failed",
        *(["- none"] if not failures else [f"- {item}" for item in failures]),
        "",
        "## Known Implementation Limitations",
        "- Preflight uses local fresh targets only; no full Magma/CVE campaign was started.",
        "- Native-TC-DGF preflight uses the shared FORMTRIG replay/log harness with native-DT-only plans.",
        "",
    ]
    (package_root / "README.md").write_text("\n".join(readme))
    tar_path = ROOT / "preflight_package.tar.gz"
    if tar_path.exists():
        tar_path.unlink()
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(package_root, arcname="preflight_package")
    return tar_path


def main() -> int:
    batch_id = time.strftime("formtrig_v3_preflight_%Y%m%dT%H%M%SZ", time.gmtime())
    batch_dir = ROOT / "results" / "preflight" / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    setup_results = ensure_fresh_targets()
    inventory = read_inventory()
    run_results: list[dict[str, object]] = setup_results
    failures: list[str] = []
    for target_id in TARGETS:
        for baseline in BASELINES:
            for mode in MODES:
                run_dir = batch_dir / "runs" / target_id / baseline / mode
                result = run_one(target_id, baseline, mode, run_dir, inventory)
                run_results.append(result)
                if result["returncode"] != 0:
                    failures.append(f"run_failed:{target_id}:{baseline}:{mode}")
                failures.extend(validate_run(run_dir))
    for target_id in TARGETS:
        for rel in [ROOT / "artifacts" / "tcir" / f"{target_id}.json", ROOT / "artifacts" / "atoms" / f"{target_id}.json", ROOT / "artifacts" / "trigger_graphs" / f"{target_id}.json"]:
            if not rel.exists():
                failures.append(f"missing_global_artifact:{rel}")
    tar_path = aggregate_and_package(batch_dir, run_results, failures)
    summary = {"batch_dir": str(batch_dir), "package": str(tar_path), "failures": failures, "status": "pass" if not failures else "fail"}
    (batch_dir / "preflight_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
