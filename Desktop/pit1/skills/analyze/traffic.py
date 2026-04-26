"""
traffic.py — Infer traffic pattern from project signals.
Used by recommend skill to decide between serverless vs dedicated server.
"""
from pathlib import Path
import json


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def detect_traffic(project_path: str) -> dict:
    """
    Returns:
    {
        "pattern": "low" | "medium" | "burst" | "realtime",
        "expected_rps": null | int,
        "reason": str,
    }

    Pattern meanings:
      low      → personal project, internal tool, < 10 rps
      medium   → startup, steady traffic, ~10-1000 rps
      burst    → event-driven, spiky (serverless friendly)
      realtime → WebSocket / streaming, latency-sensitive
    """
    root = Path(project_path)

    # WebSocket → realtime
    deps_text = _collect_deps_text(root)
    if any(s in deps_text for s in ["websockets", "socketio", "socket.io", "ws\n", "ably", "pusher"]):
        return {"pattern": "realtime", "expected_rps": None, "reason": "WebSocket dependency detected"}

    # Serverless config → burst
    for f in ["serverless.yml", "serverless.yaml"]:
        if (root / f).exists():
            return {"pattern": "burst", "expected_rps": None, "reason": "Serverless config found"}

    # Cron / worker → medium
    if (root / "Procfile").exists():
        content = _read(root / "Procfile")
        if "worker" in content or "clock" in content:
            return {"pattern": "medium", "expected_rps": None, "reason": "Worker process in Procfile"}

    # Check README for traffic hints
    readme = _read(root / "README.md").lower()
    if any(k in readme for k in ["million users", "high traffic", "scale", "load balancer"]):
        return {"pattern": "medium", "expected_rps": None, "reason": "High-scale keywords in README"}

    # Default: low (most hackathon/side projects)
    return {"pattern": "low", "expected_rps": None, "reason": "No traffic signals detected, defaulting to low"}


def _collect_deps_text(root: Path) -> str:
    text = ""
    for f in ["requirements.txt", "package.json", "pyproject.toml"]:
        text += _read(root / f)
    return text.lower()