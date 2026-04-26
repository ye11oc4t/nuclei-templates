"""
deps.py — Dependency analysis: framework detection + special requirement flags.
"""
from pathlib import Path
import json


FRAMEWORK_MAP = {
    # Python
    "fastapi": "fastapi", "flask": "flask", "django": "django",
    "starlette": "starlette", "tornado": "tornado", "sanic": "sanic",
    # Node
    "express": "express", "fastify": "fastify", "koa": "koa",
    "nestjs": "nestjs", "@nestjs/core": "nestjs",
    "next": "nextjs", "nuxt": "nuxt", "remix": "remix",
    "astro": "astro", "svelte": "svelte", "vite": "vite",
    "gatsby": "gatsby",
    # Worker
    "celery": "celery", "dramatiq": "dramatiq", "rq": "rq",
    "bullmq": "bullmq", "bull": "bull",
    # GPU/ML
    "torch": "pytorch", "tensorflow": "tensorflow",
    "transformers": "transformers",
    # Realtime
    "socketio": "socketio", "python-socketio": "socketio",
    "socket.io": "socketio", "ws": "websocket",
    "websockets": "websocket",
}

SPECIAL_FLAGS = {
    "needs_gpu": ["torch", "tensorflow", "transformers", "cuda", "jax"],
    "needs_worker": ["celery", "dramatiq", "rq", "bullmq", "bull", "arq"],
    "needs_websocket": ["socketio", "python-socketio", "socket.io", "websockets", "ws", "ably", "pusher"],
}


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def detect_deps(project_path: str) -> dict:
    """
    Returns:
    {
        "framework": "fastapi",
        "all_deps": [...],
        "needs_gpu": bool,
        "needs_worker": bool,
        "needs_websocket": bool,
    }
    """
    root = Path(project_path)
    all_deps = []

    # requirements.txt
    req = root / "requirements.txt"
    if req.exists():
        for line in _read(req).splitlines():
            dep = line.split("==")[0].split(">=")[0].split("[")[0].strip().lower()
            if dep:
                all_deps.append(dep)

    # pyproject.toml
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        content = _read(pyproject)
        for line in content.splitlines():
            if '"' in line and any(c in line for c in [">=", "==", "^", "~"]):
                dep = line.strip().strip('"').split('"')[0].split(">=")[0].split("==")[0].strip().lower()
                if dep:
                    all_deps.append(dep)

    # package.json
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(_read(pkg))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            all_deps.extend([d.lower() for d in deps.keys()])
        except Exception:
            pass

    # Framework detection (first match wins)
    framework = "unknown"
    for dep in all_deps:
        if dep in FRAMEWORK_MAP:
            framework = FRAMEWORK_MAP[dep]
            break

    # Special flags
    flags = {}
    for flag, keywords in SPECIAL_FLAGS.items():
        flags[flag] = any(dep in keywords for dep in all_deps)

    return {
        "framework": framework,
        "all_deps": list(set(all_deps)),
        **flags,
    }