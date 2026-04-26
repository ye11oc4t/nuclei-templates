"""
pit1 CLI — AI-powered infra agent for cmux
Entry point: pit1 deploy ./myapp
"""
import typer
import json
import sys
from pathlib import Path
from typing import Optional
from rich.console import Console

app = typer.Typer(
    name="pit1",
    help="AI infra agent. Analyze code → recommend infra → deploy.",
    add_completion=False,
)
console = Console(stderr=True)  # logs to stderr; stdout = machine-readable JSON


@app.command()
def deploy(
    path: str = typer.Argument(".", help="Path to project root"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip approval prompts"),
    output: str = typer.Option("pretty", "--output", "-o", help="Output format: pretty | json"),
    budget: Optional[str] = typer.Option(None, "--budget", help="Monthly budget hint: $0 | $10 | $30 | unlimited"),
    provider: Optional[str] = typer.Option(None, "--provider", help="Force a specific provider (aws, gcp, hetzner, vultr, oracle, vercel)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Analyze & recommend only, skip execution"),
):
    """Analyze code and deploy to optimal infrastructure."""
    from core.strategist import Strategist
    from core.context import Context

    ctx = Context(
        project_path=path,
        yes=yes,
        output_format=output,
        budget=budget,
        forced_provider=provider,
        dry_run=dry_run,
    )

    strategist = Strategist(ctx)
    result = strategist.run()

    if output == "json":
        print(json.dumps(result, indent=2))
    else:
        _pretty_result(result)

    sys.exit(0 if result.get("status") == "success" else 1)


@app.command()
def analyze(
    path: str = typer.Argument(".", help="Path to project root"),
    output: str = typer.Option("pretty", "--output", "-o"),
):
    """Analyze project only (no deployment)."""
    from skills.analyze import run_analyze

    result = run_analyze(path)
    if output == "json":
        print(json.dumps(result, indent=2))
    else:
        console.print_json(json.dumps(result, indent=2))


@app.command()
def recommend(
    path: str = typer.Argument(".", help="Path to project root"),
    budget: Optional[str] = typer.Option(None, "--budget"),
    output: str = typer.Option("pretty", "--output", "-o"),
):
    """Recommend infra without deploying."""
    from skills.analyze import run_analyze
    from skills.recommend import run_recommend

    analysis = run_analyze(path)
    result = run_recommend(analysis, budget=budget)

    if output == "json":
        print(json.dumps(result, indent=2))
    else:
        console.print_json(json.dumps(result, indent=2))


@app.command()
def plan(
    path: str = typer.Argument(".", help="Path to project root"),
    output: str = typer.Option("pretty", "--output", "-o"),
):
    """Show architecture plan (analyze + recommend + diagram, no deploy)."""
    from core.strategist import Strategist
    from core.context import Context

    ctx = Context(project_path=path, dry_run=True, output_format=output)
    result = Strategist(ctx).run()

    if output == "json":
        print(json.dumps(result, indent=2))
    else:
        _pretty_result(result)


def _pretty_result(result: dict):
    from rich.panel import Panel
    from rich.table import Table

    status = result.get("status", "unknown")
    color = "green" if status == "success" else "red"
    console.print(Panel(f"[{color}]Status: {status}[/{color}]", title="pit1"))

    if "analysis" in result:
        a = result["analysis"]
        console.print(f"[bold]Runtime:[/bold] {a.get('runtime', '?')}")
        console.print(f"[bold]Framework:[/bold] {a.get('framework', '?')}")
        console.print(f"[bold]DB:[/bold] {', '.join(a.get('databases', [])) or 'none'}")

    if "recommendation" in result:
        r = result["recommendation"]
        console.print(f"[bold]Recommended:[/bold] {r.get('vendor', '?')} — {r.get('tier', '?')}")
        console.print(f"[bold]Est. cost:[/bold] {r.get('estimated_cost', '?')}/mo")

    if "outputs" in result:
        for k, v in result["outputs"].items():
            console.print(f"[dim]{k}:[/dim] {v}")


if __name__ == "__main__":
    app()