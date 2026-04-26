"""DigitalOcean provider config"""
API_BASE = "https://api.digitalocean.com/v2"
REGIONS = {
    "nyc3": "New York",
    "sgp1": "Singapore",  # closest to Korea
    "ams3": "Amsterdam",
    "fra1": "Frankfurt",
}
TIERS = {
    "s-1vcpu-1gb":  {"vcpu": 1, "ram_gb": 1, "disk_gb": 25,  "price": "$6/mo"},
    "s-1vcpu-2gb":  {"vcpu": 1, "ram_gb": 2, "disk_gb": 50,  "price": "$12/mo"},
    "s-2vcpu-4gb":  {"vcpu": 2, "ram_gb": 4, "disk_gb": 80,  "price": "$24/mo"},
}
IaC_SUPPORT = True   # Official Terraform provider available
DEPLOY_METHOD = "api_direct"