"""Unit tests for analyze skill."""
import pytest
import tempfile
import os
from pathlib import Path


def _make_project(files: dict) -> str:
    """Create a temp project dir with given files."""
    d = tempfile.mkdtemp()
    for name, content in files.items():
        p = Path(d) / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return d


# ── runtime tests ─────────────────────────────────────────────────────────────

class TestRuntime:
    def test_static_html(self):
        from skills.analyze.runtime import detect_runtime
        d = _make_project({"index.html": "<h1>hi</h1>"})
        r = detect_runtime(d)
        assert r["runtime"] == "static"

    def test_fastapi_is_dynamic(self):
        from skills.analyze.runtime import detect_runtime
        d = _make_project({
            "main.py": "from fastapi import FastAPI\napp = FastAPI()",
            "requirements.txt": "fastapi\nuvicorn",
        })
        r = detect_runtime(d)
        assert r["runtime"] == "dynamic"

    def test_nextjs_export_is_static(self):
        from skills.analyze.runtime import detect_runtime
        d = _make_project({
            "next.config.js": "module.exports = { output: 'export' }",
            "package.json": '{"dependencies": {"next": "14.0.0"}}',
        })
        r = detect_runtime(d)
        assert r["runtime"] == "static"
        assert r["edge_case"] == "nextjs_export"

    def test_nextjs_app_router_is_dynamic(self):
        from skills.analyze.runtime import detect_runtime
        d = _make_project({
            "next.config.js": "module.exports = {}",
            "package.json": '{"dependencies": {"next": "14.0.0"}}',
            "app/page.tsx": "export default function Page() { return <div/> }",
        })
        r = detect_runtime(d)
        assert r["runtime"] == "dynamic"

    def test_supabase_static(self):
        from skills.analyze.runtime import detect_runtime
        d = _make_project({
            "package.json": '{"dependencies": {"@supabase/supabase-js": "2.0.0"}}',
            "index.html": "<html/>",
        })
        r = detect_runtime(d)
        assert r["runtime"] == "static"


# ── db tests ──────────────────────────────────────────────────────────────────

class TestDB:
    def test_no_db(self):
        from skills.analyze.db import detect_db
        d = _make_project({"index.html": "<h1/>"})
        r = detect_db(d)
        assert r["db_type"] == "none"
        assert r["databases"] == []

    def test_postgres_self_hosted(self):
        from skills.analyze.db import detect_db
        d = _make_project({"requirements.txt": "fastapi\npsycopg2-binary\nuvicorn"})
        r = detect_db(d)
        assert r["db_type"] == "self_hosted"
        assert "postgresql" in r["databases"]

    def test_supabase_is_external_saas(self):
        from skills.analyze.db import detect_db
        d = _make_project({"package.json": '{"dependencies": {"@supabase/supabase-js": "2.0"}}'})
        r = detect_db(d)
        assert r["db_type"] == "external_saas"

    def test_redis_detected(self):
        from skills.analyze.db import detect_db
        d = _make_project({"requirements.txt": "redis\naioredis"})
        r = detect_db(d)
        assert "redis" in r["databases"]


# ── deps tests ────────────────────────────────────────────────────────────────

class TestDeps:
    def test_celery_needs_worker(self):
        from skills.analyze.deps import detect_deps
        d = _make_project({"requirements.txt": "celery\nfastapi"})
        r = detect_deps(d)
        assert r["needs_worker"] is True

    def test_socketio_needs_websocket(self):
        from skills.analyze.deps import detect_deps
        d = _make_project({"requirements.txt": "python-socketio\nfastapi"})
        r = detect_deps(d)
        assert r["needs_websocket"] is True

    def test_torch_needs_gpu(self):
        from skills.analyze.deps import detect_deps
        d = _make_project({"requirements.txt": "torch\ntransformers"})
        r = detect_deps(d)
        assert r["needs_gpu"] is True

    def test_framework_detection_fastapi(self):
        from skills.analyze.deps import detect_deps
        d = _make_project({"requirements.txt": "fastapi\nuvicorn\nsqlalchemy"})
        r = detect_deps(d)
        assert r["framework"] == "fastapi"


# ── recommend tests ───────────────────────────────────────────────────────────

class TestRecommend:
    def _static_analysis(self):
        return {
            "runtime": "static", "framework": "nextjs", "language": "node",
            "databases": [], "db_type": "none", "needs_gpu": False,
            "needs_worker": False, "needs_websocket": False,
            "suggested_components": ["cdn", "object_storage"],
            "traffic_pattern": "low",
        }

    def test_static_recommends_vercel(self):
        from skills.recommend import run_recommend
        r = run_recommend(self._static_analysis())
        assert r["vendor"] == "vercel"
        assert r["estimated_cost"] == "$0"

    def test_budget_zero_recommends_oracle(self):
        from skills.recommend import run_recommend
        analysis = {**self._static_analysis(), "runtime": "dynamic",
                    "suggested_components": ["app_server"]}
        r = run_recommend(analysis, budget="$0")
        assert r["vendor"] == "oracle"
        assert r["browser_automate"] is True

    def test_budget_10_recommends_hetzner(self):
        from skills.recommend import run_recommend
        analysis = {**self._static_analysis(), "runtime": "dynamic",
                    "suggested_components": ["app_server"]}
        r = run_recommend(analysis, budget="$10")
        assert r["vendor"] == "hetzner"

    def test_gpu_recommends_runpod(self):
        from skills.recommend import run_recommend
        analysis = {**self._static_analysis(), "runtime": "dynamic",
                    "needs_gpu": True, "suggested_components": ["gpu_instance"]}
        r = run_recommend(analysis)
        assert r["vendor"] == "runpod"


# ── router tests ──────────────────────────────────────────────────────────────

class TestRouter:
    def _ctx(self, runtime="dynamic", vendor="hetzner", dry_run=False):
        from core.context import Context
        ctx = Context(dry_run=dry_run)
        ctx.analysis = {"runtime": runtime}
        ctx.recommendation = {"vendor": vendor}
        return ctx

    def test_static_vercel(self):
        from core.router import route_execution
        ctx = self._ctx(runtime="static", vendor="vercel")
        assert route_execution(ctx) == "static_vercel"

    def test_static_aws_is_s3(self):
        from core.router import route_execution
        ctx = self._ctx(runtime="static", vendor="aws")
        assert route_execution(ctx) == "static_s3"

    def test_hetzner_is_api_direct(self):
        from core.router import route_execution
        ctx = self._ctx(runtime="dynamic", vendor="hetzner")
        assert route_execution(ctx) == "api_direct"

    def test_oracle_is_browser(self):
        from core.router import route_execution
        ctx = self._ctx(runtime="dynamic", vendor="oracle")
        assert route_execution(ctx) == "browser_automate"

    def test_aws_is_terraform(self):
        from core.router import route_execution
        ctx = self._ctx(runtime="dynamic", vendor="aws")
        assert route_execution(ctx) == "iac_terraform"

    def test_dry_run(self):
        from core.router import route_execution
        ctx = self._ctx(dry_run=True)
        assert route_execution(ctx) == "dry_run"