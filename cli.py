#!/usr/bin/env python3
"""
SmartRoute CLI — Extract and route an inspector message from a text file.

Uses Agent A's parse_message() pipeline for extraction.

Usage:
    python cli.py message.txt
    python cli.py message.txt --raw
    echo "Permit #12345 approved at 123 Main St" | python cli.py -
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table

from smartroute import parse_message
from smartroute.models import SmartrouteRecord

console = Console()


def _color_for_confidence(confidence: float) -> str:
    if confidence >= 0.7:
        return "green"
    elif confidence >= 0.4:
        return "yellow"
    else:
        return "red"


def _record_to_display_dict(record: SmartrouteRecord) -> dict:
    """Extract the key fields into a clean display dict."""
    date_str = ""
    if record.inspection.inspection_date:
        date_str = record.inspection.inspection_date.strftime("%Y-%m-%d")
    elif record.release.release_date:
        date_str = record.release.release_date.strftime("%Y-%m-%d")

    inspector = ""
    for c in record.contacts:
        if c.role.value == "inspector":
            inspector = c.name
            break

    return {
        "permit_number": record.permit.permit_number,
        "inspection_date": date_str,
        "status": record.inspection.status.value,
        "site_address": record.site.address_full,
        "structure_type": record.release.structure_type,
        "inspector": inspector,
    }


def display_result(record: SmartrouteRecord) -> None:
    """Print a rich-formatted extraction & routing summary."""
    color = _color_for_confidence(record.quality.confidence_overall)
    display = _record_to_display_dict(record)

    # ── Extraction Panel ──
    console.print()
    console.print(
        Panel(
            JSON(json.dumps(display, indent=2)),
            title="[bold cyan]📋 Extracted Record[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    # ── Routing Panel ──
    op = record.operational
    action_icon = "🚨" if op.action_required else "✅"
    priority_colors = {"low": "green", "normal": "yellow", "high": "bold red"}
    p_color = priority_colors.get(op.priority.value, "white")

    route_table = Table(show_header=False, box=None, padding=(0, 2))
    route_table.add_column("Key", style="bold")
    route_table.add_column("Value")
    route_table.add_row("Team", f"[bold]{op.route_to_team.value}[/bold]")
    route_table.add_row("Action Required", f"{action_icon} {'YES' if op.action_required else 'No'}")
    route_table.add_row("Priority", f"[{p_color}]{op.priority.value.upper()}[/{p_color}]")
    if op.action_reason:
        route_table.add_row("Reason", op.action_reason)
    if op.recommended_actions:
        route_table.add_row("Actions", "; ".join(op.recommended_actions))

    console.print(
        Panel(
            route_table,
            title="[bold magenta]🔀 Routing Decision[/bold magenta]",
            border_style="magenta",
            padding=(1, 2),
        )
    )

    # ── Confidence Bar ──
    bar_width = 30
    conf = record.quality.confidence_overall
    filled = int(conf * bar_width)
    bar = f"[{color}]{'█' * filled}[/{color}]{'░' * (bar_width - filled)}"
    console.print(f"\n  Confidence: {bar} [{color}]{conf*100:.0f}%[/{color}]")

    # Missing fields
    if record.quality.missing_required_fields:
        console.print(f"  [dim]Missing: {', '.join(record.quality.missing_required_fields)}[/dim]")
    console.print()


def main() -> None:
    parser = argparse.ArgumentParser(description="SmartRoute CLI — Extract & route inspector messages")
    parser.add_argument("input", type=str, help="Path to .txt file or '-' for stdin")
    parser.add_argument("--raw", action="store_true", help="Output raw JSON only")
    args = parser.parse_args()

    if args.input == "-":
        raw_text = sys.stdin.read()
    else:
        path = Path(args.input)
        if not path.exists():
            console.print(f"[red]Error: File not found: {path}[/red]")
            sys.exit(1)
        raw_text = path.read_text()

    if not raw_text.strip():
        console.print("[red]Error: Empty input[/red]")
        sys.exit(1)

    record = parse_message(raw_text)

    if args.raw:
        print(json.dumps(record.to_dict(), indent=2, default=str))
    else:
        console.print(f"\n[dim]Input: {len(raw_text)} characters[/dim]")
        display_result(record)

    sys.exit(0 if record.quality.confidence_overall >= 0.3 else 1)


if __name__ == "__main__":
    main()
