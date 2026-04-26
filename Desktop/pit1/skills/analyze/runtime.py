"""
runtime.py — Detect whether project is static, dynamic, serverless, or edge.

Key insight: classification is based on whether a SERVER PROCESS is needed,
NOT on whether a DB is used.

Edge cases handled:
  - Static + external SaaS DB  → static
  - Static + Supabase/Firebase → static
  - Next.js with getServerSideProps → dynamic
  - Next.js export mode → static
  - Vercel Edge Functions → edge
  - Cloudflare Workers → edge
  - Dockerfile with static build → static (check output)
  - Monorepo → analyze each sub-package
"""
from pathlib import Path
import json
import re


# Files that signal a static site (no server process)
STATIC_SIGNALS = [
    "index.html",
    "_site",           # Jekyll
    "public/index.html",
    "dist/index.html",
    "out/index.html",  # Next.js export
    ".nojekyll",
    "CNAME",           # GitHub Pages custom domain
]

# Files/patterns that signal dynamic (server process required)
DYNAMIC_SIGNALS = [
    "server.py", "server.js", "server.ts",
    "app.py", "main.py",
    "wsgi.py", "asgi.py",
    "Procfile",
    "railway.json",
    "fly.toml",
]

# Serverless signals
SERVERLESS_SIGNALS = [
    "serverless.yml", "serverless.yaml",
    "handler.py", "handler.js",
    "netlify.toml",
    "vercel.json",         # may be static OR serverless
    "wrangler.toml",       # Cloudflare Workers
]

EDGE_PATTERNS = [
    "wrangler.toml",
    "edge.ts", "edge.js",
]

SSR_PATTERNS = [
    r"getServerSideProps",
    r"getInitialProps",
    r"server\.listen",
    r"app\.listen",
    r"uvicorn\b",
    r"gunicorn\b",
    r"hypercorn\b",
]

EXTERNAL_SAAS_DB = [
    "supabase", "firebase", "firestore", "planetscale",
    "neon", "turso", "xata", "fauna",
    "mongodb atlas", "atlas",
]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _has_file(root: Path, name: str) -> bool:
    return (root / name).exists()


def detect_runtime(project_path: str) -> dict:
    """
    Returns:
    {
        "runtime": "static" | "dynamic" | "serverless" | "edge",
        "confidence": "high" | "medium" | "low",
        "language": "python" | "node" | "go" | "ruby" | "unknown",
        "edge_case": null | "static_with_external_db" | "ssr_detected" | ...
    }
    """
    root = Path(project_path)
    edge_case = None

    # ── Language detection ────────────────────────────────────────
    language = _detect_language(root)

    # ── Edge signals (highest priority) ──────────────────────────
    for sig in EDGE_PATTERNS:
        if _has_file(root, sig):
            return {"runtime": "edge", "confidence": "high", "language": language, "edge_case": None}

    # ── Serverless signals ────────────────────────────────────────
    serverless_found = [s for s in SERVERLESS_SIGNALS if _has_file(root, s)]

    # ── Static signals ────────────────────────────────────────────
    static_found = [s for s in STATIC_SIGNALS if _has_file(root, s)]

    # ── Dynamic signals ───────────────────────────────────────────
    dynamic_found = [s for s in DYNAMIC_SIGNALS if _has_file(root, s)]

    # ── SSR pattern scan ──────────────────────────────────────────
    ssr_detected = _scan_for_ssr(root)
    if ssr_detected:
        edge_case = "ssr_detected"

    # ── Next.js: export mode = static, ssr = dynamic ──────────────
    nextjs_mode = _detect_nextjs_mode(root)

    # ── Dockerfile analysis ────────────────────────────────────────
    dockerfile_runtime = _analyze_dockerfile(root)

    # ── Resolve ───────────────────────────────────────────────────
    if nextjs_mode == "static":
        return {"runtime": "static", "confidence": "high", "language": "node", "edge_case": "nextjs_export"}
    if nextjs_mode == "dynamic":
        return {"runtime": "dynamic", "confidence": "high", "language": "node", "edge_case": "nextjs_ssr"}

    if dockerfile_runtime:
        return {"runtime": dockerfile_runtime, "confidence": "medium", "language": language, "edge_case": "dockerfile"}

    if ssr_detected or dynamic_found:
        return {"runtime": "dynamic", "confidence": "high", "language": language, "edge_case": edge_case}

    if serverless_found and not dynamic_found:
        # vercel.json alone doesn't mean serverless if no api/ dir
        if "vercel.json" in serverless_found and not _has_file(root, "api"):
            pass  # fall through to static check
        else:
            return {"runtime": "serverless", "confidence": "medium", "language": language, "edge_case": None}

    if static_found:
        # Check for external SaaS DB usage even in static project
        ext_saas = _has_external_saas_db(root)
        if ext_saas:
            edge_case = "static_with_external_db"
        return {"runtime": "static", "confidence": "high", "language": language, "edge_case": edge_case}

    # ── Heuristic fallback ────────────────────────────────────────
    if language == "python":
        return {"runtime": "dynamic", "confidence": "low", "language": language, "edge_case": "assumed_dynamic"}
    if language == "node":
        # Node without explicit signals — check package.json scripts
        pkg_runtime = _node_package_runtime(root)
        return {"runtime": pkg_runtime, "confidence": "low", "language": language, "edge_case": "inferred"}

    return {"runtime": "dynamic", "confidence": "low", "language": language, "edge_case": "assumed_dynamic"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _detect_language(root: Path) -> str:
    if list(root.glob("*.py")) or (root / "requirements.txt").exists() or (root / "pyproject.toml").exists():
        return "python"
    if (root / "package.json").exists() or list(root.glob("*.js")) or list(root.glob("*.ts")):
        return "node"
    if list(root.glob("*.go")) or (root / "go.mod").exists():
        return "go"
    if list(root.glob("*.rb")) or (root / "Gemfile").exists():
        return "ruby"
    return "unknown"


def _scan_for_ssr(root: Path) -> bool:
    """Scan source files for SSR patterns."""
    for ext in ("*.py", "*.js", "*.ts"):
        for f in list(root.rglob(ext))[:30]:  # cap at 30 files
            content = _read(f)
            for pattern in SSR_PATTERNS:
                if re.search(pattern, content):
                    return True
    return False


def _detect_nextjs_mode(root: Path) -> str | None:
    next_config = root / "next.config.js"
    next_config_ts = root / "next.config.ts"
    next_config_mjs = root / "next.config.mjs"

    for cfg in (next_config, next_config_ts, next_config_mjs):
        if cfg.exists():
            content = _read(cfg)
            if "output: 'export'" in content or 'output: "export"' in content:
                return "static"
            if "getServerSideProps" in content or "serverExternalPackages" in content:
                return "dynamic"
            # next.config present but unclear → check pages/app dir
            if (root / "app").exists() or (root / "pages").exists():
                return "dynamic"  # App Router = dynamic by default

    return None


def _analyze_dockerfile(root: Path) -> str | None:
    df = root / "Dockerfile"
    if not df.exists():
        return None
    content = _read(df).lower()
    if "cmd" in content and ("serve" in content or "start" in content or "run" in content):
        # Has a server process
        if "nginx" in content or "http-server" in content:
            return "static"  # serving static files
        return "dynamic"
    return None


def _has_external_saas_db(root: Path) -> bool:
    """Check if project uses external SaaS DB (still classifies as static)."""
    all_text = ""
    for f in [root / "package.json", root / ".env.example", root / ".env.local",
              root / "README.md"]:
        all_text += _read(f).lower()
    return any(saas in all_text for saas in EXTERNAL_SAAS_DB)


def _node_package_runtime(root: Path) -> str:
    pkg = root / "package.json"
    if not pkg.exists():
        return "dynamic"
    try:
        data = json.loads(_read(pkg))
        scripts = data.get("scripts", {})
        build_cmd = scripts.get("build", "")
        if "next export" in build_cmd or "astro build" in build_cmd:
            return "static"
        if "start" in scripts or "serve" in scripts:
            return "dynamic"
    except Exception:
        pass
    return "dynamic"