"""
cli.py — Wraps external CLIs (vercel, gh) for static site deployment.
All commands are non-interactive (agent-safe).
"""
from utils.shell import run_cmd
from utils.logger import log
from core.context import Context


def deploy_vercel(ctx: Context) -> dict:
    """Deploy static site to Vercel using vercel CLI."""
    log.info("Deploying to Vercel...")

    project_path = ctx.analysis.get("project_path", ".")

    # vercel --prod --yes = non-interactive
    result = run_cmd(
        ["vercel", "--prod", "--yes", "--cwd", project_path],
        capture=True,
    )

    if result["returncode"] != 0:
        return _fail("vercel", result["stderr"])

    # Parse URL from vercel output
    url = _extract_url(result["stdout"])
    log.info(f"Vercel deployment URL: {url}")

    return {
        "strategy": "static_vercel",
        "status": "success",
        "outputs": {"url": url, "provider": "vercel"},
        "error": None,
    }


def deploy_github_pages(ctx: Context) -> dict:
    """Deploy to GitHub Pages using gh CLI."""
    log.info("Deploying to GitHub Pages...")

    project_path = ctx.analysis.get("project_path", ".")
    framework = ctx.analysis.get("framework", "unknown")

    # Detect build output dir
    build_dir = _detect_build_dir(project_path, framework)

    result = run_cmd(
        ["gh", "pages", "deploy", build_dir, "--yes"],
        capture=True,
        cwd=project_path,
    )

    if result["returncode"] != 0:
        # Fallback: git push to gh-pages branch
        return _deploy_ghpages_git(project_path, build_dir)

    return {
        "strategy": "static_ghpages",
        "status": "success",
        "outputs": {"provider": "github_pages"},
        "error": None,
    }


def _deploy_ghpages_git(project_path: str, build_dir: str) -> dict:
    """Fallback: push build dir to gh-pages branch."""
    cmds = [
        ["git", "add", "-f", build_dir],
        ["git", "commit", "-m", "pit1: deploy to gh-pages"],
        ["git", "subtree", "push", "--prefix", build_dir, "origin", "gh-pages"],
    ]
    for cmd in cmds:
        result = run_cmd(cmd, capture=True, cwd=project_path)
        if result["returncode"] != 0:
            return _fail("github_pages_git", result["stderr"])

    return {
        "strategy": "static_ghpages",
        "status": "success",
        "outputs": {"provider": "github_pages", "method": "git_subtree"},
        "error": None,
    }


def _detect_build_dir(project_path: str, framework: str) -> str:
    from pathlib import Path
    root = Path(project_path)
    candidates = {
        "nextjs": ["out", "dist", ".next"],
        "nuxt": [".output/public", "dist"],
        "astro": ["dist"],
        "vite": ["dist"],
        "gatsby": ["public"],
        "svelte": ["public", "build"],
    }
    for dirname in candidates.get(framework, ["dist", "build", "public", "out"]):
        if (root / dirname).exists():
            return dirname
    return "dist"


def _extract_url(stdout: str) -> str:
    import re
    match = re.search(r"https://[^\s]+\.vercel\.app", stdout)
    return match.group(0) if match else "unknown"


def _fail(provider: str, error: str) -> dict:
    return {
        "strategy": f"static_{provider}",
        "status": "failed",
        "outputs": {},
        "error": error,
    }