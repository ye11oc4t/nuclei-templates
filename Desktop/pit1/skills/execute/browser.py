"""
browser.py — cmux browser automation for vendors with no IaC/API support.
Primary target: Oracle Free Tier console.

Uses cmux's built-in browser pane + snapshot-based element interaction.
"""
import subprocess
import time
from utils.logger import log
from utils.shell import run_cmd
from core.context import Context


def deploy_via_browser(ctx: Context) -> dict:
    """
    Automate cloud console via cmux browser pane.
    Currently implements Oracle Free Tier VM creation.
    """
    vendor = ctx.recommendation.get("vendor", "oracle").lower()

    if vendor == "oracle":
        return _deploy_oracle(ctx)

    return {
        "strategy": "browser_automate",
        "status": "failed",
        "outputs": {},
        "error": f"Browser automation not implemented for vendor: {vendor}",
    }


def _deploy_oracle(ctx: Context) -> dict:
    """
    Automate Oracle Cloud Free Tier VM provisioning via cmux browser.
    Requires: user is logged in to cloud.oracle.com already.
    """
    log.info("Starting Oracle Free Tier browser automation...")

    framework = ctx.analysis.get("framework", "app")
    analysis = ctx.analysis

    # Open Oracle Cloud console in cmux browser pane
    _cmux_browser_open("https://cloud.oracle.com/compute/instances/create")
    time.sleep(3)

    # Take snapshot to see current state
    snapshot = _cmux_snapshot()
    log.debug(f"Browser snapshot: {snapshot[:200]}")

    # Fill VM name
    _cmux_click_element(snapshot, label="Name", value=f"pit1-{framework}")
    time.sleep(0.5)

    # Select shape: VM.Standard.A1.Flex (Always Free)
    _cmux_click_element(snapshot, label="Change Shape")
    time.sleep(1)
    snapshot = _cmux_snapshot()
    _cmux_click_element(snapshot, label="Ampere")
    _cmux_click_element(snapshot, label="VM.Standard.A1.Flex")
    _cmux_click_element(snapshot, label="Select Shape")
    time.sleep(0.5)

    # Set OCPU and memory to max free tier
    _cmux_set_field(snapshot, field="OCPU count", value="4")
    _cmux_set_field(snapshot, field="Memory (GB)", value="24")

    # Boot volume: Ubuntu 22.04 or 24.04
    _cmux_click_element(snapshot, label="Change Image")
    time.sleep(1)
    snapshot = _cmux_snapshot()
    _cmux_click_element(snapshot, label="Ubuntu")
    _cmux_click_element(snapshot, label="Select Image")
    time.sleep(0.5)

    # Network: default VCN is fine for free tier
    # SSH key: paste if available
    _maybe_inject_ssh_key(snapshot)

    # Create instance
    _cmux_click_element(snapshot, label="Create")

    # Wait and notify
    _cmux_notify("pit1", f"Oracle VM creation initiated for {framework}")

    return {
        "strategy": "browser_automate",
        "status": "success",
        "outputs": {
            "provider": "oracle",
            "note": "VM creation initiated. Check Oracle console for IP (takes ~2 min).",
        },
        "error": None,
    }


# ── cmux browser primitives ───────────────────────────────────────────────────

def _cmux_browser_open(url: str):
    """Open URL in a new cmux browser pane."""
    run_cmd(["cmux", "new-pane", "--type", "browser", "--url", url], capture=True)


def _cmux_snapshot() -> str:
    """Get current browser snapshot (element tree)."""
    result = run_cmd(["cmux", "browser", "snapshot"], capture=True)
    return result.get("stdout", "")


def _cmux_click_element(snapshot: str, label: str, value: str = None):
    """Click an element by its label. Optionally fill a value."""
    cmd = ["cmux", "browser", "click", "--label", label]
    if value:
        cmd += ["--value", value]
    run_cmd(cmd, capture=True)


def _cmux_set_field(snapshot: str, field: str, value: str):
    """Set a form field value."""
    run_cmd(["cmux", "browser", "fill", "--field", field, "--value", value], capture=True)


def _cmux_notify(title: str, message: str):
    """Send cmux notification."""
    run_cmd(["cmux", "notify", "--title", title, "--message", message], capture=True)


def _maybe_inject_ssh_key(snapshot: str):
    """Inject SSH public key if available."""
    import os
    from pathlib import Path

    ssh_key_path = Path.home() / ".ssh" / "id_rsa.pub"
    if not ssh_key_path.exists():
        ssh_key_path = Path.home() / ".ssh" / "id_ed25519.pub"

    if ssh_key_path.exists():
        pub_key = ssh_key_path.read_text().strip()
        _cmux_set_field(snapshot, field="SSH keys", value=pub_key)
        log.info(f"Injected SSH key from {ssh_key_path}")
    else:
        log.warning("No SSH public key found (~/.ssh/id_rsa.pub). VM may be inaccessible.")