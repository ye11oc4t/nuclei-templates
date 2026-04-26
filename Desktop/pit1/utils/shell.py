"""utils/shell.py — safe subprocess wrapper."""
import subprocess
from utils.logger import log


def run_cmd(cmd: list[str], capture: bool = False, cwd: str = None, timeout: int = 120) -> dict:
    """
    Run a shell command.
    Returns {"returncode": int, "stdout": str, "stderr": str}
    """
    log.debug(f"$ {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            cwd=cwd,
            timeout=timeout,
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout or "",
            "stderr": result.stderr or "",
        }
    except FileNotFoundError:
        return {"returncode": 127, "stdout": "", "stderr": f"Command not found: {cmd[0]}"}
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "stdout": "", "stderr": f"Timed out after {timeout}s"}
    except Exception as e:
        return {"returncode": -1, "stdout": "", "stderr": str(e)}