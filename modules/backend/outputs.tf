output "api-root-url" {
  description = "Root URL of the application API."
  value       = aws_apigatewayv2_stage.public_api_prod.invoke_url
}

