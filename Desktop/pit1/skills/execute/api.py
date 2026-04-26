"""
api.py — Direct REST API calls to cloud vendors (no IaC needed).
Supports: Hetzner, Vultr, DigitalOcean, S3 static hosting.
"""
import os
import httpx
from utils.logger import log
from core.context import Context


def deploy_via_api(ctx: Context) -> dict:
    """Route to correct API based on recommended vendor."""
    vendor = ctx.recommendation.get("vendor", "").lower()
    tier = ctx.recommendation.get("tier", "cx11")

    if vendor == "hetzner":
        return _deploy_hetzner(ctx, tier)
    if vendor == "vultr":
        return _deploy_vultr(ctx, tier)
    if vendor == "digitalocean" or vendor == "do":
        return _deploy_digitalocean(ctx, tier)

    return _fail(vendor, f"Unsupported vendor for api_direct: {vendor}")


def deploy_s3_static(ctx: Context) -> dict:
    """Deploy static site to S3 + CloudFront."""
    import boto3
    from pathlib import Path

    project_path = ctx.analysis.get("project_path", ".")
    bucket_name = f"pit1-{Path(project_path).name.lower()}-{os.urandom(4).hex()}"

    try:
        s3 = boto3.client("s3")
        s3.create_bucket(Bucket=bucket_name)
        s3.put_bucket_website(
            Bucket=bucket_name,
            WebsiteConfiguration={"IndexDocument": {"Suffix": "index.html"}}
        )
        # Upload build dir
        build_dir = _detect_build_dir(project_path, ctx.analysis.get("framework", ""))
        _upload_dir_to_s3(s3, build_dir, bucket_name)

        url = f"http://{bucket_name}.s3-website.amazonaws.com"
        return {"strategy": "static_s3", "status": "success",
                "outputs": {"url": url, "bucket": bucket_name}, "error": None}
    except Exception as e:
        return _fail("s3", str(e))


# ── Hetzner ──────────────────────────────────────────────────────────────────

def _deploy_hetzner(ctx: Context, tier: str) -> dict:
    api_key = os.environ.get("HETZNER_API_TOKEN")
    if not api_key:
        return _fail("hetzner", "HETZNER_API_TOKEN env var not set")

    server_type = _hetzner_tier(tier)
    name = f"pit1-{ctx.analysis.get('framework', 'app')}"

    # Get startup script (cloud-init)
    user_data = _cloud_init_script(ctx)

    resp = httpx.post(
        "https://api.hetzner.cloud/v1/servers",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "name": name,
            "server_type": server_type,
            "image": "ubuntu-24.04",
            "user_data": user_data,
        },
        timeout=30,
    )

    if resp.status_code not in (200, 201):
        return _fail("hetzner", f"API error {resp.status_code}: {resp.text}")

    data = resp.json()
    server = data.get("server", {})
    ip = server.get("public_net", {}).get("ipv4", {}).get("ip", "?")

    return {
        "strategy": "api_direct",
        "status": "success",
        "outputs": {"ip": ip, "provider": "hetzner", "server_id": server.get("id")},
        "error": None,
    }


def _hetzner_tier(tier: str) -> str:
    tier_lower = tier.lower()
    if "cx11" in tier_lower or "$4" in tier_lower:
        return "cx11"
    if "cx21" in tier_lower or "$12" in tier_lower:
        return "cx21"
    return "cx11"  # default cheapest


# ── Vultr ─────────────────────────────────────────────────────────────────────

def _deploy_vultr(ctx: Context, tier: str) -> dict:
    api_key = os.environ.get("VULTR_API_KEY")
    if not api_key:
        return _fail("vultr", "VULTR_API_KEY env var not set")

    user_data = _cloud_init_script(ctx)

    resp = httpx.post(
        "https://api.vultr.com/v2/instances",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "region": "ewr",          # New Jersey (closest to Korea for cheapest)
            "plan": "vc2-1c-1gb",     # $6/mo
            "os_id": 2136,            # Ubuntu 24.04
            "user_data": user_data,
            "label": f"pit1-{ctx.analysis.get('framework', 'app')}",
        },
        timeout=30,
    )

    if resp.status_code not in (200, 201, 202):
        return _fail("vultr", f"API error {resp.status_code}: {resp.text}")

    data = resp.json().get("instance", {})
    return {
        "strategy": "api_direct",
        "status": "success",
        "outputs": {"ip": data.get("main_ip", "?"), "provider": "vultr",
                    "instance_id": data.get("id")},
        "error": None,
    }


# ── DigitalOcean ─────────────────────────────────────────────────────────────

def _deploy_digitalocean(ctx: Context, tier: str) -> dict:
    api_key = os.environ.get("DIGITALOCEAN_TOKEN")
    if not api_key:
        return _fail("digitalocean", "DIGITALOCEAN_TOKEN env var not set")

    user_data = _cloud_init_script(ctx)

    resp = httpx.post(
        "https://api.digitalocean.com/v2/droplets",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "name": f"pit1-{ctx.analysis.get('framework', 'app')}",
            "region": "nyc3",
            "size": "s-1vcpu-1gb",   # $6/mo
            "image": "ubuntu-24-04-x64",
            "user_data": user_data,
        },
        timeout=30,
    )

    if resp.status_code not in (200, 201, 202):
        return _fail("digitalocean", f"API error {resp.status_code}: {resp.text}")

    data = resp.json().get("droplet", {})
    return {
        "strategy": "api_direct",
        "status": "success",
        "outputs": {"provider": "digitalocean", "droplet_id": data.get("id")},
        "error": None,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cloud_init_script(ctx: Context) -> str:
    """Generate cloud-init user_data script to auto-deploy the app."""
    framework = ctx.analysis.get("framework", "unknown")
    dockerfile_path = ctx.generated.get("dockerfile")

    if dockerfile_path:
        return f"""#!/bin/bash
apt-get update -y && apt-get install -y docker.io git
systemctl start docker
git clone $GIT_REPO /app || true
cd /app && docker build -t pit1app . && docker run -d -p 80:8000 pit1app
"""
    return f"""#!/bin/bash
apt-get update -y
echo "pit1: no Dockerfile found, manual setup required for {framework}"
"""


def _detect_build_dir(project_path: str, framework: str) -> str:
    from pathlib import Path
    root = Path(project_path)
    for d in ["dist", "out", "build", "public", ".output/public"]:
        if (root / d).exists():
            return str(root / d)
    return str(root)


def _upload_dir_to_s3(s3, local_dir: str, bucket: str):
    from pathlib import Path
    import mimetypes
    for p in Path(local_dir).rglob("*"):
        if p.is_file():
            key = str(p.relative_to(local_dir))
            ct, _ = mimetypes.guess_type(str(p))
            s3.upload_file(str(p), bucket, key,
                           ExtraArgs={"ContentType": ct or "application/octet-stream"})


def _fail(provider: str, error: str) -> dict:
    log.error(f"[{provider}] {error}")
    return {"strategy": "api_direct", "status": "failed", "outputs": {}, "error": error}