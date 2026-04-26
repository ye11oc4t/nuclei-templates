"""GCP provider config"""
REGIONS = ["us-central1", "asia-northeast3"]  # asia-northeast3 = Seoul
FREE_TIER = {
    "compute": "e2-micro (1 per month)",
    "cloud_run": "2M requests/mo",
    "cloud_sql": "none (paid)",
    "gcs": "5GB",
}
TIERS = {
    "e2-micro":   "$0 (free tier 1/mo)",
    "e2-small":   "$13/mo",
    "e2-medium":  "$27/mo",
}
IaC_SUPPORT = True