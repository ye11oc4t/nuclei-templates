"""
Analyze skill — entry point.
Runs all sub-analyzers and merges results.
"""
from skills.analyze.runtime import detect_runtime
from skills.analyze.db import detect_db
from skills.analyze.deps import detect_deps
from skills.analyze.traffic import detect_traffic
from utils.logger import log


def run_analyze(project_path: str) -> dict:
    """
    Full project analysis.
    Returns unified analysis dict consumed by recommend + generate skills.
    """
    log.info(f"Analyzing: {project_path}")

    runtime_info = detect_runtime(project_path)
    db_info = detect_db(project_path)
    deps_info = detect_deps(project_path)
    traffic_info = detect_traffic(project_path)

    analysis = {
        # Core classification
        "runtime": runtime_info["runtime"],           # static | dynamic | serverless | edge
        "runtime_confidence": runtime_info["confidence"],
        "edge_case": runtime_info.get("edge_case"),   # e.g. "static_with_external_db"

        # App characteristics
        "framework": deps_info["framework"],
        "language": runtime_info.get("language", "unknown"),
        "all_deps": deps_info["all_deps"],

        # DB / storage
        "databases": db_info["databases"],
        "db_type": db_info["db_type"],               # none | external_saas | self_hosted
        "storage": db_info.get("storage", []),

        # Special requirements (affect vendor routing)
        "needs_gpu": deps_info["needs_gpu"],
        "needs_worker": deps_info["needs_worker"],
        "needs_websocket": deps_info["needs_websocket"],
        "needs_persistent_storage": db_info.get("needs_persistent_storage", False),

        # Traffic hints
        "traffic_pattern": traffic_info["pattern"],   # low | medium | burst | realtime
        "expected_rps": traffic_info.get("expected_rps"),

        # Suggested infra components (for IaC generation)
        "suggested_components": _suggest_components(runtime_info, db_info, deps_info),

        # Raw path (for later skills)
        "project_path": project_path,
    }

    log.debug(f"Analysis result: {analysis}")
    return analysis


def _suggest_components(runtime_info: dict, db_info: dict, deps_info: dict) -> list:
    components = []

    runtime = runtime_info["runtime"]
    if runtime == "static":
        components.append("cdn")
        components.append("object_storage")
    elif runtime in ("dynamic", "serverless"):
        components.append("app_server")

    db_type = db_info["db_type"]
    if db_type == "self_hosted":
        for db in db_info["databases"]:
            components.append(f"managed_{db}" if db != "sqlite" else "sqlite")
    elif db_type == "external_saas":
        components.append("external_db_saas")

    if deps_info["needs_worker"]:
        components.append("worker")
    if deps_info["needs_websocket"]:
        components.append("realtime_server")
    if deps_info["needs_gpu"]:
        components.append("gpu_instance")

    return components