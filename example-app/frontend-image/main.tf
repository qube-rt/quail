data "aws_caller_identity" "primary" {}

module "frontend-image" {
  source = "../../modules/frontend-ecr"

  # Project definition vars
  project-name    = var.project-name
  region-primary  = var.region-primary
  account-primary = data.aws_caller_identity.primary.account_id

  # Tag config
  resource-tags = var.resource-tags

  # Application config
  api-root-url = var.api-root-url
  account-name-labels = var.account-name-labels

  # Okta Auth config
  jwt-issuer    = var.auth_server_issuer
  jwt-client-id = var.oauth_app_client_id
}
