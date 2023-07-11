
provider "aws" {
  profile = var.profile
  region  = var.region-primary
}

provider "aws" {
  profile = var.profile
  region  = "us-east-1"
  alias   = "secondary-region"
}

provider "aws" {
  profile = var.profile-second-account
  region  = "eu-west-1"
  alias   = "secondary-account-main-region"
}

data "aws_caller_identity" "primary" {
}

data "aws_caller_identity" "second" {
  provider = aws.secondary-account-main-region
}

provider "okta" {
  org_name  = var.okta-org-name
  base_url  = var.okta-base-url
  api_token = var.okta-api-token
}
