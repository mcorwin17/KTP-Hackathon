#!/usr/bin/env python3
"""
Evaluation Harness — Measure Agent A's extraction accuracy against ground truth.

Uses Agent A's `parse_message()` as the extraction engine and compares output
against synthetic ground truth using EM, FM, and routing accuracy metrics.

Usage:
    python tools/eval.py --synthetic-dir data/synthetic/ --output eval/report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table
from Levenshtein import distance as levenshtein_distance

# Agent A's extraction + routing pipeline
from smartroute import parse_message
from smartroute.models import SmartrouteRecord

console = Console()

# ── Metric Functions ─────────────────────────────────────────────────────────


def exact_match(predicted: str, expected: str) -> float:
    return 1.0 if predicted.strip().upper() == expected.strip().upper() else 0.0


def fuzzy_match(predicted: str, expected: str) -> float:
    if not predicted or not expected:
        return 0.0
    max_len = max(len(predicted), len(expected))
    if max_len == 0:
        return 1.0
    dist = levenshtein_distance(predicted.lower(), expected.lower())
    return round(1.0 - dist / max_len, 4)


def _extract_fields_from_record(record: SmartrouteRecord) -> dict:
    """Pull key fields from Agent A's SmartrouteRecord for comparison."""
    permit = record.permit.permit_number or ""
    status = record.inspection.status.value if record.inspection.status else "unknown"
    site = record.site.address_full or ""
    structure_type = record.release.structure_type or ""

    # Date: use inspection_date or release_date
    inspection_date = ""
    if record.inspection.inspection_date:
        inspection_date = record.inspection.inspection_date.strftime("%Y-%m-%d")
    elif record.inspection.completed_date:
        inspection_date = record.inspection.completed_date.strftime("%Y-%m-%d")
    elif record.release.release_date:
        inspection_date = record.release.release_date.strftime("%Y-%m-%d")

    inspector = ""
    for c in record.contacts:
        if c.role.value == "inspector":
            inspector = c.name
            break

    # Routing
    team = record.operational.route_to_team.value
    action = record.operational.action_required
    priority = record.operational.priority.value

    return {
        "permit_number": permit,
        "inspection_date": inspection_date,
        "status": status,
        "site_address": site,
        "structure_type": structure_type,
        "inspector_name": inspector,
        "route_team": team,
        "action_required": action,
        "priority": priority,
        "confidence": record.quality.confidence_overall,
    }


# ── Per-Message Evaluation ───────────────────────────────────────────────────


def evaluate_message(raw_text: str, expected: dict) -> dict:
    """Evaluate Agent A's extraction against ground truth."""
    record = parse_message(raw_text)
    extracted = _extract_fields_from_record(record)

    # Exact matches
    permit_em = exact_match(extracted["permit_number"], expected["permit_number"])
    date_em = exact_match(extracted["inspection_date"], expected.get("inspection_date", ""))
    status_em = exact_match(extracted["status"], expected.get("status", "unknown"))
    type_em = fuzzy_match(extracted["structure_type"], expected.get("structure_type", ""))

    # Fuzzy match for address
    address_fm = fuzzy_match(extracted["site_address"], expected.get("site_address", ""))

    # Routing: compare action_required based on status
    # Expected: fail → action_required=True, pass → action_required=False
    expected_action = expected.get("status", "unknown") in ("fail", "partial")
    action_correct = extracted["action_required"] == expected_action

    return {
        "message_id": expected.get("message_id", "unknown"),
        "template_type": expected.get("template_type", "unknown"),
        "confidence": extracted["confidence"],
        "permit_number": {
            "predicted": extracted["permit_number"],
            "expected": expected["permit_number"],
            "exact_match": permit_em,
        },
        "inspection_date": {
            "predicted": extracted["inspection_date"],
            "expected": expected.get("inspection_date", ""),
            "exact_match": date_em,
        },
        "site_address": {
            "predicted": extracted["site_address"],
            "expected": expected.get("site_address", ""),
            "fuzzy_score": address_fm,
        },
        "status": {
            "predicted": extracted["status"],
            "expected": expected.get("status", "unknown"),
            "exact_match": status_em,
        },
        "structure_type": {
            "predicted": extracted["structure_type"],
            "expected": expected.get("structure_type", ""),
            "fuzzy_score": type_em,
        },
        "routing": {
            "team": extracted["route_team"],
            "action_correct": action_correct,
            "predicted_action": extracted["action_required"],
            "expected_action": expected_action,
        },
    }


# ── Aggregate Metrics ────────────────────────────────────────────────────────


def compute_aggregate(results: list[dict]) -> dict:
    n = len(results)
    if n == 0:
        return {}
    agg = {
        "total_messages": n,
        "permit_em": sum(r["permit_number"]["exact_match"] for r in results) / n,
        "date_em": sum(r["inspection_date"]["exact_match"] for r in results) / n,
        "address_fm_avg": sum(r["site_address"]["fuzzy_score"] for r in results) / n,
        "status_em": sum(r["status"]["exact_match"] for r in results) / n,
        "structure_type_fm": sum(r["structure_type"]["fuzzy_score"] for r in results) / n,
        "routing_action_accuracy": sum(1 for r in results if r["routing"]["action_correct"]) / n,
        "avg_confidence": sum(r["confidence"] for r in results) / n,
    }

    # Per-template breakdown
    template_groups: dict[str, list[dict]] = {}
    for r in results:
        template_groups.setdefault(r["template_type"], []).append(r)

    agg["per_template"] = {}
    for template, group in sorted(template_groups.items()):
        m = len(group)
        agg["per_template"][template] = {
            "count": m,
            "permit_em": sum(r["permit_number"]["exact_match"] for r in group) / m,
            "date_em": sum(r["inspection_date"]["exact_match"] for r in group) / m,
            "address_fm_avg": sum(r["site_address"]["fuzzy_score"] for r in group) / m,
            "status_em": sum(r["status"]["exact_match"] for r in group) / m,
            "routing_action_accuracy": sum(1 for r in group if r["routing"]["action_correct"]) / m,
        }

    scored = []
    for r in results:
        combined = (r["permit_number"]["exact_match"] * 0.3 + r["inspection_date"]["exact_match"] * 0.25
                    + r["site_address"]["fuzzy_score"] * 0.2 + r["status"]["exact_match"] * 0.15
                    + (1.0 if r["routing"]["action_correct"] else 0.0) * 0.1)
        scored.append((combined, r))
    scored.sort(key=lambda x: x[0])
    agg["worst_10"] = [s[1]["message_id"] for s in scored[:10]]
    return agg


# ── Report Display ───────────────────────────────────────────────────────────

def _fmt(val: float) -> str:
    pct = val * 100
    color = "green" if pct >= 80 else "yellow" if pct >= 60 else "red"
    return f"[{color}]{pct:.1f}%[/{color}]"


def print_report(agg: dict) -> None:
    console.print("\n[bold cyan]═══ SmartRoute Evaluation Report ═══[/bold cyan]\n")
    summary = Table(title="Aggregate Metrics", show_header=True, header_style="bold magenta")
    summary.add_column("Metric", style="cyan")
    summary.add_column("Score", style="green", justify="right")
    summary.add_row("Permit # (EM)", _fmt(agg["permit_em"]))
    summary.add_row("Inspection Date (EM)", _fmt(agg["date_em"]))
    summary.add_row("Address (FM avg)", _fmt(agg["address_fm_avg"]))
    summary.add_row("Status (EM)", _fmt(agg["status_em"]))
    summary.add_row("Structure Type (FM)", _fmt(agg["structure_type_fm"]))
    summary.add_row("Routing Action Accuracy", _fmt(agg["routing_action_accuracy"]))
    summary.add_row("Avg Confidence", _fmt(agg["avg_confidence"]))
    console.print(summary)

    if "per_template" in agg:
        tmpl = Table(title="\nPer-Template Breakdown", show_header=True, header_style="bold magenta")
        tmpl.add_column("Template", style="cyan")
        tmpl.add_column("Count", justify="right")
        tmpl.add_column("Permit EM", justify="right")
        tmpl.add_column("Date EM", justify="right")
        tmpl.add_column("Address FM", justify="right")
        tmpl.add_column("Status EM", justify="right")
        for t, d in agg["per_template"].items():
            tmpl.add_row(t, str(d["count"]), _fmt(d["permit_em"]), _fmt(d["date_em"]),
                         _fmt(d["address_fm_avg"]), _fmt(d["status_em"]))
        console.print(tmpl)

    if "worst_10" in agg:
        console.print(f"\n[bold red]Worst 10 messages:[/bold red] {', '.join(agg['worst_10'])}")
    console.print()


def generate_markdown_report(agg: dict, results: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# SmartRoute Evaluation Report", "",
        f"**Total messages evaluated:** {agg['total_messages']}",
        f"**Generated:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "",
        "---", "",
        "## Aggregate Metrics", "",
        "| Metric | Score |", "|--------|-------|",
        f"| Permit # (Exact Match) | {agg['permit_em']*100:.1f}% |",
        f"| Inspection Date (Exact Match) | {agg['date_em']*100:.1f}% |",
        f"| Site Address (Fuzzy Match avg) | {agg['address_fm_avg']*100:.1f}% |",
        f"| Status (Exact Match) | {agg['status_em']*100:.1f}% |",
        f"| Structure Type (Fuzzy Match) | {agg['structure_type_fm']*100:.1f}% |",
        f"| Routing Action Accuracy | {agg['routing_action_accuracy']*100:.1f}% |",
        f"| Average Confidence | {agg['avg_confidence']*100:.1f}% |", "",
        "---", "",
        "## Per-Template Breakdown", "",
        "| Template | Count | Permit EM | Date EM | Address FM | Status EM |",
        "|----------|-------|-----------|---------|------------|-----------|",
    ]
    for t, d in agg.get("per_template", {}).items():
        lines.append(f"| {t} | {d['count']} | {d['permit_em']*100:.1f}% | {d['date_em']*100:.1f}% | {d['address_fm_avg']*100:.1f}% | {d['status_em']*100:.1f}% |")
    lines.extend(["", "---", "", "## Worst 10 Messages", ""])
    for msg_id in agg.get("worst_10", []):
        r = next((r for r in results if r["message_id"] == msg_id), None)
        if r:
            lines.extend([
                f"### {msg_id} (template: {r['template_type']})", "",
                f"- **Permit**: `{r['permit_number']['predicted']}` vs `{r['permit_number']['expected']}` — EM: {r['permit_number']['exact_match']}",
                f"- **Date**: `{r['inspection_date']['predicted']}` vs `{r['inspection_date']['expected']}` — EM: {r['inspection_date']['exact_match']}",
                f"- **Address**: FM score {r['site_address']['fuzzy_score']:.3f}",
                f"- **Status**: `{r['status']['predicted']}` vs `{r['status']['expected']}`",
                f"- **Routing**: action {'✅' if r['routing']['action_correct'] else '❌'}", "",
            ])
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    console.print(f"[green]✅ Report written to {output_path}[/green]")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate extraction accuracy")
    parser.add_argument("--synthetic-dir", "-d", type=Path, default=Path("data/synthetic"))
    parser.add_argument("--ground-truth", "-g", type=Path, default=None)
    parser.add_argument("--output", "-o", type=Path, default=Path("eval/report.json"))
    parser.add_argument("--report-md", type=Path, default=Path("eval/report.md"))
    args = parser.parse_args()

    gt_path = args.ground_truth or (args.synthetic_dir / "ground_truth.json")
    if not gt_path.exists():
        console.print(f"[red]Error: {gt_path} not found[/red]")
        sys.exit(1)

    with open(gt_path) as f:
        ground_truth = json.load(f)

    console.print(f"[cyan]Evaluating {len(ground_truth)} messages with Agent A's pipeline...[/cyan]")

    results = []
    for gt_entry in ground_truth:
        msg_file = args.synthetic_dir / f"{gt_entry['message_id']}.txt"
        if not msg_file.exists():
            continue
        raw_text = msg_file.read_text()
        result = evaluate_message(raw_text, gt_entry)
        results.append(result)

    agg = compute_aggregate(results)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump({"aggregate": agg, "per_message": results}, f, indent=2, default=str)

    print_report(agg)
    generate_markdown_report(agg, results, args.report_md)


if __name__ == "__main__":
    main()
