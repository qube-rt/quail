output "application_acs_url" {
  description = "The value required for SSO app configuration"
  value       = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.region-primary}.amazoncognito.com/saml2/idpresponse"
}

output "aws_sso_saml_audience" {
  description = "SAML Audience used for SSO app config"
  value       = "urn:amazon:cognito:sp:${aws_cognito_user_pool.api-auth.id}"
}

output "aws_sso_start_urls" {
  description = "Start url for the SSO app config"
  value = { for key, value in aws_cognito_identity_provider.sso :
    key => "https://${var.hosting-domain}/auth-initiate?identity_provider=${value.provider_name}"
  }
}

output "aws_sso_localhost_start_urls" {
  description = "Start url for the SSO app config"
  value = var.support-localhost-urls ? { for key, value in aws_cognito_identity_provider.sso :
    key => "http://localhost:3000/auth-initiate?identity_provider=${value.provider_name}"
  } : {}
}

output "api-root-url" {
  description = "Root URL of the application API."
  value       = aws_apigatewayv2_stage.prod.invoke_url
}

output "cognito-domain" {
  description = "Domain of the Cognito user pool."
  value       = aws_cognito_user_pool_domain.main.domain
}

output "cognito-client-id" {
  description = "ID of the Cognito client used for authentication."
  value       = aws_cognito_user_pool_client.main.id
}
