"""Hetzner provider config"""
API_BASE = "https://api.hetzner.cloud/v1"
REGIONS = ["nbg1", "fsn1", "hel1", "ash", "hil", "sin"]  # sin = Singapore (closest to Korea)
TIERS = {
    "cx11":  {"vcpu": 2,  "ram_gb": 2,  "disk_gb": 20,  "price": "$4/mo"},
    "cx21":  {"vcpu": 3,  "ram_gb": 4,  "disk_gb": 40,  "price": "$12/mo"},
    "cx31":  {"vcpu": 4,  "ram_gb": 8,  "disk_gb": 80,  "price": "$20/mo"},
    "cx41":  {"vcpu": 8,  "ram_gb": 16, "disk_gb": 160, "price": "$38/mo"},
    "ccx13": {"vcpu": 2,  "ram_gb": 8,  "disk_gb": 80,  "price": "$17/mo"},  # dedicated
}
IaC_SUPPORT = False  # No official Terraform provider (community exists)
DEPLOY_METHOD = "api_direct"