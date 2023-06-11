
provider "aws" {
  profile = var.profile
  region  = var.region-primary
}

provider "aws" {
  profile = var.profile
  region  = "us-east-1"
  alias   = "secondary"
}

data "aws_caller_identity" "primary" {
}

provider "okta" {
  org_name  = var.okta-org-name
  base_url  = var.okta-base-url
  api_token = var.okta-api-token
}
