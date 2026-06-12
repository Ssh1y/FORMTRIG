#!/usr/bin/env python3
"""Audit runtime FORMTRIG progress signals after a native AFL++ run.

This is an evidence gate, not an observer. It reads the compiled lift spec and
the structured progress log, then reports whether exact distance components
behave like usable TC-rooted progress signals. It never feeds T back into
non-trigger guidance; terminal status is used only for post-run validation.
"""

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Tuple


DISTANCE_COMPONENT_KINDS = {1, 2, 3}
EPSILON = 1.0e-9


class DistanceComponent(NamedTuple):
    event_kind: str
    site_id: str
    kind: int
    atom_id: int
    priority: int
    source_id: int
    context_hash: int
    metric: str
    spec_line: int


def parse_int(value: Any, *, default: Optional[int] = None) -> Optional[int]:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    token = str(value).strip()
    if not token:
        return default
    try:
        return int(token, 0)
    except ValueError:
        try:
            return int(token, 16)
        except ValueError:
            return default


def parse_context_hash(value: Any) -> Optional[int]:
    if isinstance(value, int):
        return value
    token = str(value or "").strip().lower()
    if not token:
        return None
    try:
        if token.startswith("0x"):
            return int(token, 16)
        if any(ch in token for ch in "abcdef") or len(token) == 16:
            return int(token, 16)
        return int(token, 10)
    except ValueError:
        return None


def finite_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        out = float(value)
    else:
        try:
            out = float(str(value))
        except (TypeError, ValueError):
            return None
    return out if math.isfinite(out) else None


def load_json(path: Optional[Path]) -> Dict[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text())


def spec_path_from_report(report_path: Path, report: Dict[str, Any]) -> Optional[Path]:
    raw = report.get("spec")
    if not raw:
        return None
    path = Path(str(raw))
    if not path.is_absolute():
        path = report_path.parent / path
    if path.is_file():
        return path
    local = report_path.parent / Path(str(raw)).name
    if local.is_file():
        return local
    return path


def parse_lift_spec(path: Path) -> List[DistanceComponent]:
    components = []  # type: List[DistanceComponent]
    for lineno, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if parts[0] != "component" or len(parts) < 12:
            continue
        kind = parse_int(parts[3])
        atom_id = parse_int(parts[4])
        priority = parse_int(parts[5])
        source_id = parse_int(parts[10])
        context_hash = parse_int(parts[11])
        if (
            kind is None
            or atom_id is None
            or priority is None
            or source_id is None
            or context_hash is None
        ):
            continue
        metric = parts[7]
        components.append(
            DistanceComponent(
                event_kind=parts[1],
                site_id=parts[2],
                kind=kind,
                atom_id=atom_id,
                priority=priority,
                source_id=source_id,
                context_hash=context_hash,
                metric=metric,
                spec_line=lineno,
            )
        )
    return components


def graph_atom_summary(paths: Iterable[Path]) -> Dict[str, Any]:
    count = 0
    categories = []  # type: List[str]
    for path in paths:
        try:
            graph = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for node in graph.get("nodes", []):
            if not isinstance(node, dict) or node.get("type") != "tc_atom":
                continue
            count += 1
            category = str(node.get("category") or "")
            if category and category not in categories:
                categories.append(category)
    return {"atom_count": count, "atom_categories": categories}


def component_key(component: DistanceComponent) -> Tuple[int, int, int, int]:
    return (
        component.kind,
        component.atom_id,
        component.source_id,
        component.context_hash,
    )


def runtime_component_key(component: Dict[str, Any]) -> Optional[Tuple[int, int, int, int]]:
    kind = parse_int(component.get("kind"))
    atom_id = parse_int(component.get("atom_id"))
    source_id = parse_int(component.get("source_id"))
    context_hash = parse_context_hash(component.get("context_hash"))
    if (
        kind is None
        or atom_id is None
        or source_id is None
        or context_hash is None
    ):
        return None
    return (kind, atom_id, source_id, context_hash)


def load_progress_events(path: Path, *, max_events: int) -> List[Dict[str, Any]]:
    events = []  # type: List[Dict[str, Any]]
    with path.open(errors="replace") as handle:
        for line in handle:
            if max_events and len(events) >= max_events:
                break
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                events.append(event)
    return events


def summarize_component(
    component: DistanceComponent,
    events: List[Dict[str, Any]],
    *,
    atom_count: int,
    min_samples: int,
) -> Dict[str, Any]:
    key = component_key(component)
    values = []  # type: List[float]
    nontrigger_values = []  # type: List[float]
    triggered_values = []  # type: List[float]
    reached_nontrigger = 0
    reached_triggered = 0
    sample_events = []  # type: List[Dict[str, Any]]

    for event in events:
        if not event.get("reached"):
            continue
        triggered = bool(event.get("triggered"))
        components = event.get("component_values")
        if not isinstance(components, list):
            continue
        matched_value = None  # type: Optional[float]
        for runtime_component in components:
            if not isinstance(runtime_component, dict):
                continue
            if runtime_component_key(runtime_component) != key:
                continue
            matched_value = finite_float(runtime_component.get("value"))
            break
        if matched_value is None:
            continue
        values.append(matched_value)
        if triggered:
            triggered_values.append(matched_value)
            reached_triggered += 1
        else:
            nontrigger_values.append(matched_value)
            reached_nontrigger += 1
        if len(sample_events) < 8:
            sample_events.append(
                {
                    "event": str(event.get("event") or ""),
                    "reason": str(event.get("reason") or ""),
                    "queue_id": event.get("queue_id"),
                    "triggered": bool(event.get("triggered")),
                    "value": matched_value,
                    "d_f": event.get("d_f"),
                }
            )

    is_distance = component.metric == "distance" or component.kind in DISTANCE_COMPONENT_KINDS
    zero_nontrigger = sum(1 for value in nontrigger_values if abs(value) <= EPSILON)
    unique_nontrigger = sorted({round(value, 9) for value in nontrigger_values})
    issues = []  # type: List[Dict[str, str]]
    if reached_nontrigger >= min_samples:
        if is_distance and zero_nontrigger:
            severity = "error" if atom_count <= 1 else "warning"
            issues.append(
                {
                    "severity": severity,
                    "reason": "distance_zero_without_terminal_trigger",
                    "detail": (
                        "exact distance reached zero in non-trigger executions; "
                        "single-atom TCs should not use this binding as native distance"
                        if atom_count <= 1
                        else "one atom can be satisfied before a compound TC triggers"
                    ),
                }
            )
        if len(unique_nontrigger) <= 1 and (not is_distance or not zero_nontrigger):
            reason = "distance_low_entropy" if is_distance else "lifted_component_low_entropy"
            issues.append(
                {
                    "severity": "warning",
                    "reason": reason,
                    "detail": (
                        "distance component was observed but did not vary"
                        if is_distance
                        else "lifted progress component was observed but did not vary"
                    ),
                }
            )
    elif reached_nontrigger == 0 and not triggered_values:
        reason = "distance_component_unobserved" if is_distance else "lifted_component_unobserved"
        issues.append(
            {
                "severity": "warning",
                "reason": reason,
                "detail": (
                    "no reached runtime samples matched this distance component"
                    if is_distance
                    else "no reached runtime samples matched this lifted component"
                ),
            }
        )

    summary = {
        "event_kind": component.event_kind,
        "site_id": component.site_id,
        "component_kind": component.kind,
        "atom_id": component.atom_id,
        "priority": component.priority,
        "source_id": str(component.source_id),
        "context_hash": f"{component.context_hash:016x}",
        "metric": component.metric,
        "is_distance": is_distance,
        "spec_line": component.spec_line,
        "samples": len(values),
        "reached_nontrigger_samples": reached_nontrigger,
        "reached_triggered_samples": reached_triggered,
        "zero_nontrigger_samples": zero_nontrigger,
        "unique_nontrigger_values": len(unique_nontrigger),
        "min_value": min(values) if values else None,
        "max_value": max(values) if values else None,
        "sample_events": sample_events,
        "issues": issues,
    }
    return summary


def build_report(
    *,
    lift_report_path: Path,
    spec_path: Optional[Path],
    progress_log_path: Path,
    trigger_graphs: List[Path],
    min_samples: int,
    max_events: int,
) -> Dict[str, Any]:
    lift_report = load_json(lift_report_path)
    resolved_spec = spec_path or spec_path_from_report(lift_report_path, lift_report)
    if resolved_spec is None:
        raise ValueError("lift report does not identify a spec path; pass --spec")
    if not resolved_spec.is_file():
        raise ValueError(f"lift spec not found: {resolved_spec}")

    progress_components = parse_lift_spec(resolved_spec)
    distance_components = [
        component
        for component in progress_components
        if component.metric == "distance" or component.kind in DISTANCE_COMPONENT_KINDS
    ]
    events = load_progress_events(progress_log_path, max_events=max_events)
    atom_summary = graph_atom_summary(trigger_graphs)
    atom_count = int(atom_summary.get("atom_count") or 0)
    component_reports = [
        summarize_component(
            component,
            events,
            atom_count=atom_count,
            min_samples=min_samples,
        )
        for component in progress_components
    ]

    issue_counts = {"error": 0, "warning": 0}
    for component in component_reports:
        for issue in component.get("issues", []):
            severity = str(issue.get("severity") or "warning")
            issue_counts[severity] = issue_counts.get(severity, 0) + 1

    if not progress_components:
        status = "no_progress_components"
    elif issue_counts.get("error", 0):
        status = "suspect"
    elif issue_counts.get("warning", 0):
        status = "weak"
    else:
        status = "ok"

    return {
        "status": status,
        "lift_report": str(lift_report_path),
        "spec": str(resolved_spec),
        "progress_log": str(progress_log_path),
        "events_read": len(events),
        "progress_components": len(progress_components),
        "distance_components": len(distance_components),
        "atom_count": atom_count,
        "atom_categories": atom_summary.get("atom_categories", []),
        "issue_counts": issue_counts,
        "components": component_reports,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check runtime health of native FORMTRIG lifted progress",
        allow_abbrev=False,
    )
    parser.add_argument("--lift-report", required=True, type=Path)
    parser.add_argument("--spec", type=Path, help="Override lift spec path")
    parser.add_argument("--progress-log", required=True, type=Path)
    parser.add_argument("--trigger-graph", action="append", default=[], type=Path)
    parser.add_argument("--report-json", type=Path)
    parser.add_argument("--min-samples", type=int, default=1)
    parser.add_argument("--max-events", type=int, default=200000)
    parser.add_argument("--fail-on-suspect", action="store_true")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    report = build_report(
        lift_report_path=args.lift_report,
        spec_path=args.spec,
        progress_log_path=args.progress_log,
        trigger_graphs=args.trigger_graph,
        min_samples=max(1, args.min_samples),
        max_events=max(0, args.max_events),
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(text)
    else:
        sys.stdout.write(text)
    if args.fail_on_suspect and report["status"] == "suspect":
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
