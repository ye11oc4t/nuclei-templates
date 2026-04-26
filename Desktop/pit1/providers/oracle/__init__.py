"""Oracle Cloud Free Tier provider config"""
CONSOLE_URL = "https://cloud.oracle.com"
REGIONS = {
    "ap-seoul-1":   "Seoul",      # Korea
    "ap-tokyo-1":   "Tokyo",
    "us-ashburn-1": "Ashburn",
    "eu-frankfurt-1": "Frankfurt",
}
FREE_TIER = {
    "arm_vm": {
        "shape": "VM.Standard.A1.Flex",
        "ocpu": 4,
        "ram_gb": 24,
        "disk_gb": 200,
        "price": "$0/mo (always free)",
        "note": "4 OCPU + 24GB RAM total across all free instances",
    },
    "amd_vm": {
        "shape": "VM.Standard.E2.1.Micro",
        "ocpu": 1,
        "ram_gb": 1,
        "disk_gb": 50,
        "price": "$0/mo",
        "count": 2,
    },
}
IaC_SUPPORT = False   # OCI Terraform provider exists but complex
DEPLOY_METHOD = "browser"  # cmux browser automation
BROWSER_AUTOMATE = True