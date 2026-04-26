"""
cmux/pane.py — cmux pane management.

When running inside cmux (CMUX_WORKSPACE_ID set):
  → each skill gets its own pane
  → updates are streamed to that pane
  → notifications use cmux notify

When running outside cmux (fallback):
  → logs to stderr via Rich
"""
import subprocess
from rich.console import Console
from utils.logger import log

console = Console(stderr=True)


class CmuxPane:
    def __init__(self, ctx):
        self.ctx = ctx
        self.panes: dict[str, str] = {}  # skill → pane_id

    def open(self, skill: str, title: str):
        """Open a new cmux pane for a skill, or log if not in cmux."""
        if not self.ctx.in_cmux:
            console.rule(f"[bold cyan]{title}[/bold cyan]")
            return

        result = _run(["cmux", "new-pane", "--split", "vertical",
                        "--title", title, "--json"])
        if result and "pane_id" in result:
            self.panes[skill] = result["pane_id"]
            log.debug(f"Opened cmux pane '{title}' → id={result['pane_id']}")

    def update(self, skill: str, message: str):
        """Write a status update to the skill's pane."""
        if not self.ctx.in_cmux:
            console.print(f"  [dim]{message}[/dim]")
            return

        pane_id = self.panes.get(skill)
        if pane_id:
            _run(["cmux", "pane", "write", "--id", pane_id, "--text", message])

    def notify(self, message: str):
        """Send a cmux notification (or print to stderr)."""
        if not self.ctx.in_cmux:
            console.print(f"\n[bold green]{message}[/bold green]")
            return

        _run(["cmux", "notify", "--title", "pit1", "--message", message])


def _run(cmd: list[str]) -> dict | None:
    """Run a cmux CLI command, return parsed JSON if available."""
    import json
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.stdout:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {"stdout": result.stdout}
    except Exception as e:
        log.debug(f"cmux cmd failed: {cmd} → {e}")
    return None