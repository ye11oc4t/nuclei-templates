"""AWS provider config"""
REGIONS = ["us-east-1", "ap-northeast-2"]  # ap-northeast-2 = Seoul
FREE_TIER = {
    "ec2": "t2.micro",
    "rds": "db.t3.micro",
    "lambda": "1M requests/mo",
    "s3": "5GB",
    "cloudfront": "1TB transfer/mo",
}
TIERS = {
    "t2.micro":   "$0 (free tier) / ~$8/mo after",
    "t3.small":   "$15/mo",
    "t3.medium":  "$30/mo",
}
IaC_SUPPORT = True