"""
parser.py — Safely parse JSON out of LLM responses.
Handles markdown fences, trailing text, etc.
"""
import json
import re
from utils.logger import log


def parse_json_response(text: str) -> dict:
    """
    Extract and parse JSON from LLM response.
    Tries multiple strategies before giving up.
    """
    # Strategy 1: Direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown code block
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Strategy 3: Find first { ... } block
    match = re.search(r"\{[\s\S]+\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    log.error(f"Failed to parse JSON from LLM response: {text[:200]}")
    return {"error": "parse_failed", "raw": text}