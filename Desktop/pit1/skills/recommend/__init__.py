"""
Recommend skill — vendor + architecture recommendation.
Uses InfraAgent (LLM) for final decision, with rule-based pre-filtering.
"""
from agents.infra_agent import InfraAgent
from utils.logger import log
from typing import Optional


# ── Rule-based fast path (no LLM needed for obvious cases) ────────────────────

STATIC_FAST_PATH = {
    "default": {
        "vendor": "vercel",
        "tier": "hobby",
        "estimated_cost": "$0",
        "architecture": ["cdn", "object_storage"],
        "iac_support": False,
        "browser_automate": False,
        "deploy_method": "cli",
        "reasoning": "Static site → Vercel Hobby tier (free)",
    }
}

BUDGET_VENDOR_MAP = {
    # (budget_max_usd, needs_gpu, needs_worker, needs_websocket) → vendor
    0:   {"vendor": "oracle", "tier": "Free Tier (4 OCPU / 24GB)", "estimated_cost": "$0",
          "iac_support": False, "browser_automate": True, "deploy_method": "browser"},
    10:  {"vendor": "hetzner", "tier": "CX11 (2 vCPU / 2GB)", "estimated_cost": "$4-7",
          "iac_support": False, "browser_automate": False, "deploy_method": "api_direct"},
    30:  {"vendor": "hetzner", "tier": "CX21 (3 vCPU / 4GB)", "estimated_cost": "$12",
          "iac_support": False, "browser_automate": False, "deploy_method": "api_direct"},
}


def run_recommend(analysis: dict, budget: Optional[str] = None,
                  forced_provider: Optional[str] = None) -> dict:
    """
    Returns recommendation dict:
    {
        "vendor": str,
        "tier": str,
        "estimated_cost": str,
        "architecture": [str, ...],
        "iac_support": bool,
        "browser_automate": bool,
        "deploy_method": str,
        "reasoning": str,
    }
    """
    log.info(f"Recommending: runtime={analysis.get('runtime')} budget={budget}")

    # Special requirements override
    if analysis.get("needs_gpu"):
        return _gpu_recommendation()

    # Static fast path (no LLM needed)
    if analysis.get("runtime") == "static" and not forced_provider:
        rec = STATIC_FAST_PATH["default"].copy()
        rec["architecture"] = analysis.get("suggested_components", ["cdn", "object_storage"])
        return rec

    # Rule-based budget path for simple dynamic apps
    if not forced_provider and not _needs_llm(analysis):
        budget_usd = _parse_budget(budget)
        rec = _budget_based_recommendation(budget_usd, analysis)
        if rec:
            rec["architecture"] = analysis.get("suggested_components", [])
            return rec

    # LLM path for complex cases
    agent = InfraAgent()
    return agent.recommend_vendor(analysis, budget=budget, forced_provider=forced_provider)


def _needs_llm(analysis: dict) -> bool:
    """Cases that genuinely need LLM reasoning."""
    return (
        analysis.get("needs_websocket")
        or analysis.get("needs_worker")
        or analysis.get("traffic_pattern") in ("burst", "realtime")
        or len(analysis.get("databases", [])) > 1
    )


def _parse_budget(budget: Optional[str]) -> float:
    if budget is None:
        return float("inf")
    cleaned = budget.replace("$", "").replace("/mo", "").strip()
    if cleaned.lower() == "unlimited":
        return float("inf")
    try:
        return float(cleaned)
    except ValueError:
        return float("inf")


def _budget_based_recommendation(budget_usd: float, analysis: dict) -> Optional[dict]:
    if budget_usd == 0:
        return {**BUDGET_VENDOR_MAP[0]}
    if budget_usd <= 10:
        return {**BUDGET_VENDOR_MAP[10]}
    if budget_usd <= 30:
        return {**BUDGET_VENDOR_MAP[30]}
    # > $30 → use LLM to pick AWS/GCP properly
    return None


def _gpu_recommendation() -> dict:
    return {
        "vendor": "runpod",
        "tier": "RTX 3090 / A100 (on-demand)",
        "estimated_cost": "varies",
        "architecture": ["gpu_instance"],
        "iac_support": False,
        "browser_automate": False,
        "deploy_method": "api_direct",
        "reasoning": "GPU dependency detected → RunPod for cost-effective GPU hosting",
    }