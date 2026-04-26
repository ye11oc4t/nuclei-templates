"""
iac_runner.py — Runs generated Terraform / OpenTofu IaC.
"""
from utils.shell import run_cmd
from utils.logger import log
from core.context import Context
from pathlib import Path


IaC_DIR = "pit1-output"


def run_terraform(ctx: Context) -> dict:
    """
    Init + plan + apply the generated Terraform.
    Uses OpenTofu if available, falls back to Terraform.
    """
    iac_dir = Path(IaC_DIR)
    if not (iac_dir / "main.tf").exists():
        return _fail("main.tf not found in pit1-output/. Run generate first.")

    binary = _detect_binary()
    log.info(f"Using IaC binary: {binary}")

    # Init
    result = run_cmd([binary, "init"], capture=True, cwd=IaC_DIR)
    if result["returncode"] != 0:
        return _fail(f"terraform init failed: {result['stderr']}")

    # Plan
    result = run_cmd([binary, "plan", "-out=pit1.plan"], capture=True, cwd=IaC_DIR)
    if result["returncode"] != 0:
        return _fail(f"terraform plan failed: {result['stderr']}")

    # Apply
    apply_cmd = [binary, "apply", "-auto-approve", "pit1.plan"]
    result = run_cmd(apply_cmd, capture=True, cwd=IaC_DIR)
    if result["returncode"] != 0:
        return _fail(f"terraform apply failed: {result['stderr']}")

    # Extract outputs
    out_result = run_cmd([binary, "output", "-json"], capture=True, cwd=IaC_DIR)
    outputs = {}
    if out_result["returncode"] == 0:
        import json
        try:
            raw = json.loads(out_result["stdout"])
            outputs = {k: v.get("value") for k, v in raw.items()}
        except Exception:
            pass

    return {
        "strategy": "iac_terraform",
        "status": "success",
        "outputs": outputs,
        "error": None,
    }


def _detect_binary() -> str:
    """Prefer OpenTofu (tofu) over Terraform."""
    import shutil
    if shutil.which("tofu"):
        return "tofu"
    if shutil.which("terraform"):
        return "terraform"
    raise RuntimeError("Neither 'tofu' nor 'terraform' found in PATH")


def _fail(error: str) -> dict:
    log.error(error)
    return {"strategy": "iac_terraform", "status": "failed", "outputs": {}, "error": error}