output "api-root-url" {
  description = "Root URL of the application API."
  value       = module.backend.api-root-url
}

output "oauth_app_client_id" {
  description = "ID of the OAuth app used for authentication"
  value       = module.okta-app.oauth_app_client_id
}

output "auth_server_issuer" {
  description = "JWT Token issuer"
  value       = module.okta-app.auth_server_issuer
}
