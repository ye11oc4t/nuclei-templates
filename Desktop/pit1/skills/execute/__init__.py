"""
Execute skill — routes to the right execution strategy.
"""
from core.context import Context
from utils.logger import log


def run_execute(ctx: Context, strategy: str) -> dict:
    """
    Dispatch to correct executor based on strategy.
    Returns:
    {
        "strategy": str,
        "status": "success" | "failed" | "pending_approval",
        "outputs": { "url": str, ... },
        "error": str | None,
    }
    """
    log.info(f"Executing strategy: {strategy}")

    try:
        if strategy == "static_vercel":
            from skills.execute.cli import deploy_vercel
            return deploy_vercel(ctx)

        elif strategy == "static_ghpages":
            from skills.execute.cli import deploy_github_pages
            return deploy_github_pages(ctx)

        elif strategy == "static_s3":
            from skills.execute.api import deploy_s3_static
            return deploy_s3_static(ctx)

        elif strategy == "iac_terraform":
            from skills.execute.iac_runner import run_terraform
            return run_terraform(ctx)

        elif strategy == "api_direct":
            from skills.execute.api import deploy_via_api
            return deploy_via_api(ctx)

        elif strategy == "browser_automate":
            from skills.execute.browser import deploy_via_browser
            return deploy_via_browser(ctx)

        elif strategy == "dry_run":
            return {"strategy": "dry_run", "status": "success", "outputs": {}, "error": None}

        else:
            return {"strategy": strategy, "status": "failed", "outputs": {},
                    "error": f"Unknown strategy: {strategy}"}

    except Exception as e:
        log.error(f"Execution failed: {e}")
        return {"strategy": strategy, "status": "failed", "outputs": {}, "error": str(e)}