"""
Context — shared state passed through the entire pipeline.
Immutable after construction; skills read from it, never write.
"""
from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass
class Context:
    project_path: str = "."
    yes: bool = False                   # skip human approval prompts
    output_format: str = "pretty"       # pretty | json
    budget: Optional[str] = None        # "$0" | "$10" | "$30" | "unlimited"
    forced_provider: Optional[str] = None
    dry_run: bool = False
    in_cmux: bool = field(default_factory=lambda: bool(os.environ.get("CMUX_WORKSPACE_ID")))

    # resolved at runtime by strategist
    analysis: dict = field(default_factory=dict)
    recommendation: dict = field(default_factory=dict)
    generated: dict = field(default_factory=dict)
    execution: dict = field(default_factory=dict)

    def budget_usd(self) -> Optional[float]:
        """Parse budget string → float. None = no constraint."""
        if self.budget is None:
            return None
        cleaned = self.budget.replace("$", "").replace("/mo", "").strip()
        if cleaned.lower() == "unlimited":
            return float("inf")
        try:
            return float(cleaned)
        except ValueError:
            return None