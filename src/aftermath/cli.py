"""Demo entry point.

    aftermath plan --pack packs/tr.yaml --has has_property --has has_vehicle

Runs the engine only. No model, no network, no AWS — which is the point: the
core is deterministic and testable, and the agents sit on top of it.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aftermath.engine import load_pack, solve
from aftermath.engine.critical_path import INFINITY
from aftermath.engine.graph import CaseGraph, CaseProfile

console = Console()

CONFIDENCE_STYLE = {
    "verified": "green",
    "common_practice": "yellow",
    "ask_a_professional": "red",
}


def cmd_plan(args: argparse.Namespace) -> int:
    pack = load_pack(args.pack)
    graph = CaseGraph(pack, CaseProfile.from_list(args.has))
    schedule = solve(graph)

    banner = f"[bold]{pack.meta.name}[/] · pack v{pack.meta.version} · {len(graph)} steps"
    if pack.meta.status == "draft":
        banner += "\n[yellow]DRAFT PACK — entries are not yet source-verified.[/]"
    console.print(Panel(banner, title="Aftermath", border_style="cyan"))

    _print_deadlines(schedule)
    _print_steps(pack, graph, schedule)
    _print_footer(graph)
    return 0


def _print_deadlines(schedule) -> None:  # noqa: ANN001
    table = Table(title="Deadlines", header_style="dim", title_justify="left")
    table.add_column("Deadline")
    table.add_column("Day", justify="right")
    table.add_column("Kind")
    table.add_column("Earliest possible", justify="right")
    table.add_column("Slack", justify="right")
    table.add_column("Status")

    for d in sorted(schedule.deadlines, key=lambda x: (not x.irreversible, x.day)):
        ready = "unreachable" if d.ready_day >= INFINITY else str(d.ready_day)
        if not d.feasible:
            status = "[red]AT RISK[/]"
        elif d.slack_days <= 14:
            status = "[yellow]TIGHT[/]"
        else:
            status = "[green]OK[/]"
        name = d.name + ("  [red]⚠ irreversible[/]" if d.irreversible else "")
        slack = "—" if d.ready_day >= INFINITY else f"{d.slack_days:+d}d"
        table.add_row(name, str(d.day), d.kind, ready, slack, status)

    console.print(table)

    for d in schedule.deadlines:
        if not (d.irreversible or not d.feasible):
            continue
        if d.kind == "action":
            line = (
                f"The filing itself cannot realistically be completed before day "
                f"{d.ready_day}."
            )
        else:
            line = (
                f"The facts needed to decide cannot realistically be known before "
                f"day {d.ready_day}."
            )
        console.print(
            Panel(
                f"[bold]{d.name}[/] — day {d.day}\n\n"
                f"{(d.consequence or '').strip()}\n\n"
                f"[dim]{line} Slack: {d.slack_days:+d} days.[/]",
                border_style="red",
                title="Irreversible" if d.irreversible else "At risk",
            )
        )


def _print_steps(pack, graph, schedule) -> None:  # noqa: ANN001
    table = Table(title="Plan", header_style="dim", title_justify="left")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Step")
    table.add_column("Institution")
    table.add_column("Earliest", justify="right")
    table.add_column("Latest start", justify="right")
    table.add_column("Slack", justify="right")
    table.add_column("Confidence")

    for i, s in enumerate(schedule.ordered(), start=1):
        step = graph.step(s.step_id)
        institution = (
            pack.institution(step.institution).name_en if step.institution else "—"
        )
        latest = "—" if s.latest_start is None else str(s.latest_start)
        if s.slack is None:
            slack = "—"
        elif s.slack <= 0:
            slack = f"[red]{s.slack:+d}d[/]"
        elif s.slack <= 7:
            slack = f"[yellow]{s.slack:+d}d[/]"
        else:
            slack = f"{s.slack:+d}d"

        style = CONFIDENCE_STYLE.get(step.confidence, "white")
        marker = "[red]●[/] " if s.on_critical_path else "  "

        table.add_row(
            str(i),
            marker + step.name_en,
            institution,
            f"{s.earliest_start}–{s.earliest_finish}",
            latest,
            slack,
            f"[{style}]{step.confidence}[/]",
        )

    console.print(table)
    console.print("[dim][red]●[/] on the critical path — no room to slip.[/]\n")


def _print_footer(graph) -> None:  # noqa: ANN001
    unreachable = graph.unreachable_artifacts()
    if unreachable:
        console.print(
            f"[yellow]Not producible in this case profile:[/] {', '.join(unreachable)}"
        )
    console.print(
        "[dim]Aftermath prepares; a human reviews and files. Nothing here is legal advice.[/]"
    )


def cmd_validate(args: argparse.Namespace) -> int:
    pack = load_pack(args.pack)
    console.print(
        f"[green]OK[/] {Path(args.pack).name}: "
        f"{len(pack.steps)} steps, {len(pack.artifacts)} artifacts, "
        f"{len(pack.deadlines)} deadlines, {len(pack.institutions)} institutions"
    )
    unsourced = [s.id for s in pack.steps if s.source is None]
    if unsourced:
        console.print(f"[yellow]{len(unsourced)} steps still have no source:[/] {', '.join(unsourced)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aftermath", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_plan = sub.add_parser("plan", help="build and schedule a case plan")
    p_plan.add_argument("--pack", default="packs/tr.yaml")
    p_plan.add_argument(
        "--has",
        action="append",
        default=[],
        help="a condition true for this estate, e.g. --has has_property",
    )
    p_plan.set_defaults(func=cmd_plan)

    p_val = sub.add_parser("validate", help="validate a rule pack")
    p_val.add_argument("--pack", default="packs/tr.yaml")
    p_val.set_defaults(func=cmd_validate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
