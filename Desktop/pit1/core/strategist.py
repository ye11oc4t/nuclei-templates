"""
Strategist — orchestrates the full pipeline:
  analyze → recommend → generate → execute → observe

Each step is a skill. Strategist injects results into Context
and opens cmux panes when running inside cmux.
"""
from core.context import Context
from core.router import route_execution
from cmux.pane import CmuxPane
from utils.logger import log


class Strategist:
    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.pane = CmuxPane(ctx)

    def run(self) -> dict:
        ctx = self.ctx
        log.info(f"Starting pit1 pipeline for: {ctx.project_path}")

        # ── Step 1: Analyze ─────────────────────────────────────────
        self.pane.open("analyze", title="🔍 Analyzer")
        from skills.analyze import run_analyze
        ctx.analysis = run_analyze(ctx.project_path)
        self.pane.update("analyze", f"Runtime: {ctx.analysis.get('runtime')} | Framework: {ctx.analysis.get('framework')}")
        log.info(f"Analysis: {ctx.analysis}")

        # ── Step 2: Recommend ────────────────────────────────────────
        self.pane.open("recommend", title="📐 Architect")
        from skills.recommend import run_recommend
        ctx.recommendation = run_recommend(ctx.analysis, budget=ctx.budget, forced_provider=ctx.forced_provider)
        self.pane.update("recommend", f"Vendor: {ctx.recommendation.get('vendor')} | {ctx.recommendation.get('estimated_cost', '?')}/mo")
        log.info(f"Recommendation: {ctx.recommendation}")

        if ctx.dry_run:
            # Generate diagram but don't execute
            self.pane.open("generate", title="📊 Diagram")
            from skills.generate import run_generate
            ctx.generated = run_generate(ctx.analysis, ctx.recommendation, diagram_only=True)
            self.pane.notify("pit1 plan complete — dry run, nothing deployed")
            return self._result("dry_run")

        # ── Step 3: Generate ─────────────────────────────────────────
        self.pane.open("generate", title="🏗️ Generator")
        from skills.generate import run_generate
        ctx.generated = run_generate(ctx.analysis, ctx.recommendation)
        log.info(f"Generated: {list(ctx.generated.keys())}")

        # ── Step 4: Execute ──────────────────────────────────────────
        strategy = route_execution(ctx)
        log.info(f"Execution strategy: {strategy}")

        if not ctx.yes:
            # Human-in-the-loop checkpoint (only when not agent mode)
            import sys
            if sys.stdin.isatty():
                confirm = input(f"\n▶ Deploy using strategy [{strategy}]? (y/n): ")
                if confirm.lower() != "y":
                    return self._result("cancelled")

        self.pane.open("execute", title="⚡ Executor")
        from skills.execute import run_execute
        ctx.execution = run_execute(ctx, strategy)
        log.info(f"Execution: {ctx.execution}")

        # ── Step 5: Observe ──────────────────────────────────────────
        self.pane.open("observe", title="👁 Observer")
        from skills.observe import run_observe
        observe_result = run_observe(ctx)

        self.pane.notify("✅ pit1 complete")
        return self._result("success", observe_result)

    def _result(self, status: str, observe: dict = None) -> dict:
        ctx = self.ctx
        return {
            "status": status,
            "analysis": ctx.analysis,
            "recommendation": ctx.recommendation,
            "outputs": ctx.execution.get("outputs", {}),
            "observe": observe or {},
        }