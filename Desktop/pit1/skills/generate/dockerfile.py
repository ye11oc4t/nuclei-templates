"""
dockerfile.py — Generate Dockerfile from project analysis.
Uses language/framework-specific templates.
"""
from pathlib import Path
from utils.logger import log

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates" / "docker"


def generate_dockerfile(analysis: dict) -> str:
    """
    Generate a Dockerfile string for the project.
    """
    language = analysis.get("language", "unknown")
    framework = analysis.get("framework", "unknown")

    template_file = _pick_template(language)
    if template_file and template_file.exists():
        return _render(template_file, analysis)

    # LLM fallback
    log.info(f"No Dockerfile template for language '{language}', using LLM...")
    from agents.infra_agent import InfraAgent
    return InfraAgent().generate_dockerfile(analysis)


def _pick_template(language: str) -> Path | None:
    mapping = {
        "python": TEMPLATES_DIR / "python.Dockerfile.jinja2",
        "node":   TEMPLATES_DIR / "node.Dockerfile.jinja2",
    }
    return mapping.get(language)


def _render(template_path: Path, analysis: dict) -> str:
    project_name = Path(analysis.get("project_path", "app")).name
    framework = analysis.get("framework", "unknown")

    try:
        from jinja2 import Template
        tmpl = Template(template_path.read_text())
        return tmpl.render(
            framework=framework,
            project_name=project_name,
        )
    except ImportError:
        # Fallback: return template with simple substitution
        content = template_path.read_text()
        content = content.replace("{{ framework }}", framework)
        content = content.replace("{{ project_name }}", project_name)
        return content