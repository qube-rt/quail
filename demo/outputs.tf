output "application_acs_url" {
  description = "The value required for SSO app configuration"
  value       = module.backend.application_acs_url
}

output "aws_sso_saml_audience" {
  description = "SAML Audience used for SSO app config"
  value       = module.backend.aws_sso_saml_audience
}

output "aws_sso_start_urls" {
  description = "Start url for the SSO app config"
  value       = module.backend.aws_sso_start_urls
}

output "aws_sso_localhost_start_urls" {
  description = "Start url for the SSO app config"
  value       = module.backend.aws_sso_localhost_start_urls
}
