output "api-root-url" {
  description = "Root URL of the application API."
  value       = aws_apigatewayv2_stage.public_api_prod.invoke_url
}

output "public-api-assumed-role" {
  description = "ARN of the assumed role of the public api"
  value       = "arn:aws:sts::${var.account-primary}:assumed-role/${aws_iam_role.public_api.name}/${aws_lambda_function.public_api.function_name}"
}

output "private-api-assumed-role" {
  description = "ARN of the assumed role of the private api"
  value       = "arn:aws:sts::${var.account-primary}:assumed-role/${aws_iam_role.private_api.name}/${aws_lambda_function.private_api.function_name}"
}

