"""
Generate skill — produce IaC, Dockerfiles, and architecture diagrams.
"""
from pathlib import Path
from utils.logger import log


def run_generate(analysis: dict, recommendation: dict, diagram_only: bool = False) -> dict:
    from skills.generate.diagram import generate_diagram

    output = {
        "iac": None,
        "dockerfile": None,
        "diagram_ascii": None,
        "diagram_mermaid": None,
        "files_written": [],
    }

    diagrams = generate_diagram(analysis, recommendation)
    output["diagram_ascii"] = diagrams["ascii"]
    output["diagram_mermaid"] = diagrams["mermaid"]

    if diagram_only:
        return output

    if recommendation.get("iac_support"):
        log.info("Generating Terraform HCL...")
        from skills.generate.iac import generate_iac
        output["iac"] = generate_iac(analysis, recommendation)
        p = _write("pit1-output/main.tf", output["iac"])
        output["files_written"].append(str(p))

    project_path = analysis.get("project_path", ".")
    if analysis.get("runtime") == "dynamic" and not (Path(project_path) / "Dockerfile").exists():
        log.info("Generating Dockerfile...")
        from skills.generate.dockerfile import generate_dockerfile
        output["dockerfile"] = generate_dockerfile(analysis)
        p = _write("pit1-output/Dockerfile", output["dockerfile"])
        output["files_written"].append(str(p))

    p = _write("pit1-output/architecture.mmd", diagrams["mermaid"])
    output["files_written"].append(str(p))

    return output


def _write(rel_path: str, content: str) -> Path:
    p = Path(rel_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    log.info(f"Written: {p}")
    return p