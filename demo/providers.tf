
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
