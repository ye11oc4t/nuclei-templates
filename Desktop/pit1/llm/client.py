"""
LLM client — wraps Anthropic API.
Single place to swap models or add retries/caching.
"""
import os
import anthropic
from utils.logger import log


class LLMClient:
    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"

    def complete(self, prompt: str, system: str = "", max_tokens: int = 1000) -> str:
        """Send a completion request, return raw text response."""
        log.debug(f"LLM call: {prompt[:100]}...")
        messages = [{"role": "user", "content": prompt}]

        resp = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )

        text = "".join(
            block.text for block in resp.content if hasattr(block, "text")
        )
        log.debug(f"LLM response: {text[:100]}...")
        return text