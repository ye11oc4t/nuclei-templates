"""
InfraAgent — the LLM-backed agent that reasons about code → infra.
Wraps llm/client.py and returns structured decisions.

Used by:
  - skills/recommend (vendor + architecture)
  - skills/generate  (IaC generation)
"""
from llm.client import LLMClient
from llm.parser import parse_json_response
from utils.logger import log
import json


SYSTEM_PROMPT = """
You are pit1's infrastructure strategist. You analyze software projects
and recommend optimal cloud infrastructure.

Rules:
- Always return valid JSON matching the requested schema.
- Consider budget constraints seriously. Prefer free/cheap tiers when budget is $0.
- Support all cloud vendors: AWS, GCP, Hetzner, Vultr, Oracle Free Tier, Vercel, GitHub Pages, S3.
- For static sites (no server process): prefer Vercel, GitHub Pages, or S3.
- For dynamic apps: match vendor to budget and requirements.
- If vendor has no Terraform support (Oracle, some others): flag browser_automate = true.
- Be concise. No explanations unless asked.
"""


class InfraAgent:
    def __init__(self):
        self.llm = LLMClient()

    def recommend_vendor(self, analysis: dict, budget: str = None, forced_provider: str = None) -> dict:
        """
        Returns vendor recommendation as structured dict.
        {
            "vendor": "hetzner",
            "tier": "CX11",
            "estimated_cost": "$10",
            "architecture": ["app_server", "managed_postgres"],
            "iac_support": true,
            "browser_automate": false,
            "reasoning": "..."
        }
        """
        if forced_provider:
            return self._forced_provider_result(forced_provider, analysis)

        prompt = f"""
Analyze this project and recommend the best cloud vendor + tier.

Project analysis:
{json.dumps(analysis, indent=2)}

Budget constraint: {budget or "no constraint"}

Return JSON only:
{{
  "vendor": "<vendor_name>",
  "tier": "<specific tier or instance type>",
  "estimated_cost": "<$/mo>",
  "architecture": ["<component1>", "<component2>"],
  "iac_support": <true|false>,
  "browser_automate": <true|false>,
  "deploy_method": "<terraform|api_direct|cli|browser>",
  "reasoning": "<one sentence>"
}}
"""
        raw = self.llm.complete(prompt, system=SYSTEM_PROMPT)
        result = parse_json_response(raw)
        log.debug(f"InfraAgent.recommend_vendor → {result}")
        return result

    def generate_iac(self, analysis: dict, recommendation: dict) -> str:
        """Generate Terraform HCL for the recommended infra."""
        prompt = f"""
Generate production-ready Terraform (HCL) for this project.

Project analysis:
{json.dumps(analysis, indent=2)}

Recommended infrastructure:
{json.dumps(recommendation, indent=2)}

Return only the Terraform HCL code. No markdown fences. No explanations.
"""
        return self.llm.complete(prompt, system=SYSTEM_PROMPT, max_tokens=4096)

    def generate_dockerfile(self, analysis: dict) -> str:
        """Generate optimized Dockerfile."""
        prompt = f"""
Generate a production Dockerfile for this project.

Project analysis:
{json.dumps(analysis, indent=2)}

Return only the Dockerfile content. No explanations.
"""
        return self.llm.complete(prompt, system=SYSTEM_PROMPT, max_tokens=2048)

    def _forced_provider_result(self, provider: str, analysis: dict) -> dict:
        """When user forces a specific provider, build a minimal recommendation."""
        BROWSER_VENDORS = {"oracle"}
        IAC_VENDORS = {"aws", "gcp", "azure"}

        return {
            "vendor": provider,
            "tier": "user-specified",
            "estimated_cost": "?",
            "architecture": analysis.get("suggested_components", []),
            "iac_support": provider in IAC_VENDORS,
            "browser_automate": provider in BROWSER_VENDORS,
            "deploy_method": "terraform" if provider in IAC_VENDORS else "api_direct",
            "reasoning": f"User forced provider: {provider}",
        }