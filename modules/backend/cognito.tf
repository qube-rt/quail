resource "aws_cognito_user_pool" "api-auth" {
  name              = "${var.project-name}-pool"
  mfa_configuration = "OFF"
  tags              = local.resource_tags

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  # Make email and profile required attributes
  # Profile stores the user group membership to determine permission level
  schema {
    name                     = "email"
    attribute_data_type      = "String"
    developer_only_attribute = false
    mutable                  = true
    required                 = true
    string_attribute_constraints {
      min_length = 0
      max_length = 2048
    }
  }

  schema {
    name                     = "profile"
    attribute_data_type      = "String"
    developer_only_attribute = false
    mutable                  = true
    required                 = true
    string_attribute_constraints {
      min_length = 0
      max_length = 2048
    }
  }

  schema {
    name                     = "nickname"
    attribute_data_type      = "String"
    developer_only_attribute = false
    mutable                  = true
    required                 = true
    string_attribute_constraints {
      min_length = 0
      max_length = 2048
    }
  }

  # Add a custom is_superuser attribute
  schema {
    name                     = "is_superuser"
    attribute_data_type      = "Number"
    developer_only_attribute = false
    mutable                  = true
    required                 = false
    number_attribute_constraints {
      min_value = 0
      max_value = 1
    }
  }
}

resource "aws_cognito_identity_provider" "sso" {
  for_each = var.sso-apps-metadata

  user_pool_id  = aws_cognito_user_pool.api-auth.id
  provider_name = "SSO-${each.key}"
  provider_type = "SAML"

  provider_details = {
    MetadataURL = each.value
  }

  attribute_mapping = {
    email                 = "email"
    profile               = "group"
    nickname              = "nickname"
    "custom:is_superuser" = "is_superuser"
  }

  # # The following fields always show up as pending changes
  # # Tracked in https://github.com/hashicorp/terraform-provider-aws/issues/4807
  # lifecycle {
  #   ignore_changes = [
  #     provider_details,
  #   ]
  # }
}

resource "random_string" "domain_suffix" {
  length  = 8
  special = false
  upper   = false
}

resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${var.project-name}-auth-domain-${random_string.domain_suffix.result}"
  user_pool_id = aws_cognito_user_pool.api-auth.id
}

resource "aws_cognito_user_pool_client" "main" {
  name                         = "${var.project-name}-client"
  user_pool_id                 = aws_cognito_user_pool.api-auth.id
  supported_identity_providers = values(aws_cognito_identity_provider.sso).*.provider_name
  refresh_token_validity       = 30

  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes = [
    "openid",
    "profile",
  ]
  callback_urls = compact([
    var.support-localhost-urls ? "http://localhost:3000/auth-callback" : "",
    "https://${var.hosting-domain}/auth-callback",
  ])
  logout_urls = [
    var.logout-url
  ]

  explicit_auth_flows = [
    "ALLOW_CUSTOM_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]

  read_attributes = [
    "email",
    "family_name",
    "given_name",
    "locale",
    "name",
    "nickname",
    "profile",
    "custom:is_superuser",
  ]
  write_attributes = [
    "email",
    "family_name",
    "given_name",
    "locale",
    "name",
    "nickname",
    "profile",
    "custom:is_superuser",
  ]
}