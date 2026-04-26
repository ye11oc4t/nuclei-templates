"""
Router — decides which execution path to take based on analysis + recommendation.
Pure logic, no I/O.
"""
from core.context import Context


def route_execution(ctx: Context) -> str:
    """
    Returns execution strategy string.
    
    Strategies:
      "static_vercel"     – static site → Vercel deploy
      "static_ghpages"    – static site → GitHub Pages
      "static_s3"         – static site → S3 + CloudFront
      "iac_terraform"     – dynamic → generate Terraform + apply
      "api_direct"        – dynamic → call cloud REST API directly
      "browser_automate"  – no IaC/API → cmux browser automation
      "dry_run"           – plan only, no execution
    """
    if ctx.dry_run:
        return "dry_run"

    analysis = ctx.analysis
    rec = ctx.recommendation

    runtime = analysis.get("runtime", "dynamic")
    vendor = rec.get("vendor", "").lower()

    if runtime == "static":
        return _route_static(vendor)
    else:
        return _route_dynamic(vendor)


def _route_static(vendor: str) -> str:
    if vendor in ("vercel", ""):
        return "static_vercel"
    if vendor in ("github_pages", "ghpages"):
        return "static_ghpages"
    if vendor == "aws":
        return "static_s3"
    return "static_vercel"  # default


def _route_dynamic(vendor: str) -> str:
    IaC_VENDORS = {"aws", "gcp", "azure"}
    API_VENDORS = {"hetzner", "vultr", "digitalocean", "do"}
    BROWSER_VENDORS = {"oracle", "oracle_free"}

    if vendor in IaC_VENDORS:
        return "iac_terraform"
    if vendor in API_VENDORS:
        return "api_direct"
    if vendor in BROWSER_VENDORS:
        return "browser_automate"
    return "iac_terraform"  # safest default