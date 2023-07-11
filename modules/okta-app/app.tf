# Okta Application Config
resource "okta_app_oauth" "quail" {
  label          = "${var.project-name}-auth"
  type           = "browser"
  grant_types    = ["authorization_code"]
  omit_secret    = true
  response_types = ["code"]

  token_endpoint_auth_method = "none"
  pkce_required              = true

  post_logout_redirect_uris = compact([
    var.support-localhost-urls ? "http://localhost:3000/" : "",
    "https://${var.hosting-domain}/",
  ])
  redirect_uris = compact([
    var.support-localhost-urls ? "http://localhost:3000/login/callback" : "",
    "https://${var.hosting-domain}/login/callback",
  ])

  groups_claim {
    name        = "groups"
    type        = "FILTER"
    filter_type = "REGEX"
    value       = ".*"
  }
}

resource "okta_trusted_origin" "quail" {
  name   = "quail-deployment"
  origin = "https://${var.hosting-domain}/"
  scopes = ["CORS"]
}

resource "okta_app_group_assignments" "quail" {
  app_id = okta_app_oauth.quail.id

  dynamic "group" {
    for_each = var.okta-groups
    content {
      id = group.value
    }
  }
}

# Okta Auth Server config
resource "okta_auth_server" "quail" {
  audiences   = ["${var.project-name}-users"]
  name        = "${var.project-name} Auth Server"
  description = "Auth server for the ${var.project-name} dashboard"
  issuer_mode = "ORG_URL"
  status      = "ACTIVE"
}

resource "okta_auth_server_scope" "groups" {
  auth_server_id   = okta_auth_server.quail.id
  name             = "groups"
  display_name     = "View your group membership"
  description      = "Allows the app to view your groups"
  consent          = "IMPLICIT"
  metadata_publish = "NO_CLIENTS"
}

resource "okta_auth_server_claim" "groups" {
  auth_server_id    = okta_auth_server.quail.id
  name              = "groups"
  value_type        = "GROUPS"
  value             = "((?!Everyone).)*"
  scopes            = ["${okta_auth_server_scope.groups.name}"]
  claim_type        = "IDENTITY"
  group_filter_type = "REGEX"
}

resource "okta_auth_server_policy" "quail_default" {
  auth_server_id   = okta_auth_server.quail.id
  status           = "ACTIVE"
  name             = "Default policy"
  description      = "Default policy"
  priority         = 1
  client_whitelist = [okta_app_oauth.quail.id]
}

resource "okta_auth_server_policy_rule" "quail_default" {
  auth_server_id = okta_auth_server.quail.id
  policy_id      = okta_auth_server_policy.quail_default.id

  status               = "ACTIVE"
  name                 = "Default policy"
  priority             = 1
  grant_type_whitelist = ["client_credentials", "authorization_code"]
  scope_whitelist      = ["*"]
  group_whitelist      = ["EVERYONE"]
}
