"""
Observe skill — post-deployment health check and cmux notification.
"""
import time
import httpx
from core.context import Context
from utils.logger import log


def run_observe(ctx: Context) -> dict:
    """
    Check deployment health and notify via cmux.
    Returns:
    {
        "healthy": bool,
        "url": str | None,
        "latency_ms": float | None,
        "checked_at": str,
    }
    """
    outputs = ctx.execution.get("outputs", {})
    url = outputs.get("url")
    provider = outputs.get("provider", "unknown")

    if not url:
        log.info("No URL to health-check (API/browser deploy — manual check needed)")
        _notify(ctx, f"✅ Deployed to {provider}. Check console for IP/URL.")
        return {"healthy": None, "url": None, "latency_ms": None, "checked_at": _now()}

    log.info(f"Health checking: {url}")
    healthy, latency = _http_check(url)

    status = "✅ Healthy" if healthy else "⚠️ Not responding yet"
    _notify(ctx, f"{status} — {url}")

    return {
        "healthy": healthy,
        "url": url,
        "latency_ms": latency,
        "checked_at": _now(),
    }


def _http_check(url: str, retries: int = 3, delay: float = 5.0):
    """Try GET request, return (healthy, latency_ms)."""
    for attempt in range(retries):
        try:
            t0 = time.time()
            resp = httpx.get(url, timeout=10, follow_redirects=True)
            latency = (time.time() - t0) * 1000
            if resp.status_code < 500:
                return True, round(latency, 1)
        except Exception as e:
            log.debug(f"Health check attempt {attempt+1} failed: {e}")
        if attempt < retries - 1:
            time.sleep(delay)
    return False, None


def _notify(ctx: Context, message: str):
    if ctx.in_cmux:
        from utils.shell import run_cmd
        run_cmd(["cmux", "notify", "--title", "pit1", "--message", message], capture=True)
    else:
        log.info(f"[notify] {message}")


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()