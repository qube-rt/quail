data "aws_caller_identity" "primary" {}

module "backend-image" {
  source = "../../modules/backend-ecr"

  # Project definition vars
  project-name    = var.project-name
  region-primary  = var.region-primary
  account-primary = data.aws_caller_identity.primary.account_id

  # Tag config
  resource-tags = var.resource-tags
}
