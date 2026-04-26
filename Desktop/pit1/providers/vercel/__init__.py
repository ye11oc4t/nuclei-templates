"""Vercel provider config"""
TIERS = {
    "hobby":   {"price": "$0/mo",  "limit": "100GB bandwidth"},
    "pro":     {"price": "$20/mo", "limit": "1TB bandwidth"},
}
DEPLOY_CMD = ["vercel", "--prod", "--yes"]
IaC_SUPPORT = False
DEPLOY_METHOD = "cli"
STATIC_ONLY = False  # supports serverless functions too