output "oauth_app_client_id" {
  description = "ID of the OAuth app used for authentication"
  value       = okta_app_oauth.quail.client_id
}

output "auth_server_issuer" {
  description = "JWT Token issuer"
  value       = okta_auth_server.quail.issuer
}
