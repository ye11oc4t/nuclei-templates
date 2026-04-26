"""
db.py — Detect database usage, type, and storage requirements.

Key distinction:
  db_type = "none"           → no DB at all
  db_type = "external_saas"  → DB is Supabase/Firebase/etc (no server needed)
  db_type = "self_hosted"    → DB needs to be provisioned (affects vendor choice)
"""
from pathlib import Path
import re
import json


SELF_HOSTED_DB_SIGNALS = {
    "postgresql": ["postgresql", "postgres", "psycopg2", "asyncpg", "pg"],
    "mysql": ["mysql", "mysqlclient", "pymysql", "mysql2"],
    "sqlite": ["sqlite3", "better-sqlite3", "sqlite"],
    "mongodb": ["pymongo", "mongoose", "motor"],
    "redis": ["redis", "aioredis", "ioredis"],
    "elasticsearch": ["elasticsearch", "@elastic/elasticsearch"],
    "cassandra": ["cassandra-driver"],
}

EXTERNAL_SAAS_SIGNALS = {
    "supabase": ["supabase", "@supabase/supabase-js"],
    "firebase": ["firebase", "firebase-admin", "firestore"],
    "planetscale": ["@planetscale/database"],
    "neon": ["@neondatabase/serverless"],
    "turso": ["@libsql/client", "libsql"],
    "xata": ["@xata.io/client"],
    "mongodb_atlas": ["mongodb"],  # could be self-hosted too, check env
}

STORAGE_SIGNALS = {
    "s3": ["boto3", "s3", "@aws-sdk/client-s3"],
    "gcs": ["google-cloud-storage", "@google-cloud/storage"],
    "r2": ["@cloudflare/workers-types"],  # Cloudflare R2
    "minio": ["minio"],
}

ENV_DB_PATTERNS = [
    r"DATABASE_URL",
    r"DB_HOST",
    r"POSTGRES(?:_URL|_HOST|QL_URL)",
    r"MONGO(?:_URL|DB_URI)",
    r"REDIS_URL",
    r"MYSQL_HOST",
]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def detect_db(project_path: str) -> dict:
    """
    Returns:
    {
        "databases": ["postgresql", "redis"],
        "db_type": "none" | "external_saas" | "self_hosted",
        "storage": ["s3"],
        "needs_persistent_storage": bool,
    }
    """
    root = Path(project_path)
    all_deps = _collect_all_deps(root)
    env_text = _collect_env_text(root)

    found_self_hosted = []
    found_saas = []
    found_storage = []

    # Check deps
    for db_name, signals in SELF_HOSTED_DB_SIGNALS.items():
        if any(s in all_deps for s in signals):
            found_self_hosted.append(db_name)

    for saas_name, signals in EXTERNAL_SAAS_SIGNALS.items():
        if any(s in all_deps for s in signals):
            # MongoDB could be Atlas (saas) or self-hosted — check env
            if saas_name == "mongodb_atlas":
                if "atlas.mongodb" in env_text or "mongodb+srv" in env_text:
                    found_saas.append("mongodb_atlas")
                else:
                    found_self_hosted.append("mongodb")
            else:
                found_saas.append(saas_name)

    for storage_name, signals in STORAGE_SIGNALS.items():
        if any(s in all_deps for s in signals):
            found_storage.append(storage_name)

    # Also check env files for DB_URL patterns
    env_db_found = any(re.search(p, env_text) for p in ENV_DB_PATTERNS)

    # Determine db_type
    if found_saas and not found_self_hosted:
        db_type = "external_saas"
        databases = found_saas
    elif found_self_hosted:
        db_type = "self_hosted"
        databases = found_self_hosted
    elif env_db_found:
        # Env hints but no dep match → assume self-hosted
        db_type = "self_hosted"
        databases = ["unknown"]
    else:
        db_type = "none"
        databases = []

    return {
        "databases": databases,
        "db_type": db_type,
        "storage": found_storage,
        "needs_persistent_storage": bool(found_self_hosted or found_storage),
    }


def _collect_all_deps(root: Path) -> list[str]:
    deps = []

    req = root / "requirements.txt"
    if req.exists():
        for line in _read(req).splitlines():
            dep = line.split("==")[0].split(">=")[0].split("[")[0].strip().lower()
            if dep:
                deps.append(dep)

    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(_read(pkg))
            all_pkg_deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            deps.extend([d.lower() for d in all_pkg_deps.keys()])
        except Exception:
            pass

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        content = _read(pyproject)
        for line in content.splitlines():
            if '"' in line and any(c in line for c in [">=", "==", "^"]):
                dep = line.strip().strip('"').split('"')[0].split(">=")[0].strip().lower()
                if dep:
                    deps.append(dep)

    return list(set(deps))


def _collect_env_text(root: Path) -> str:
    text = ""
    for env_file in [".env", ".env.example", ".env.local", ".env.sample"]:
        text += _read(root / env_file)
    return text