# CloudWatch log group
resource "aws_cloudwatch_log_group" "api_gateway_public" {
  name              = "/aws/gateway/${aws_apigatewayv2_api.public.name}"
  retention_in_days = local.cloudwatch_log_retention
  tags              = local.resource_tags
}

# API Gateway + stage
resource "aws_apigatewayv2_api" "public" {
  name          = "${var.project-name}-public-api"
  protocol_type = "HTTP"
  tags          = local.resource_tags
  # CORS can be configured either here or at the application level
  # Defining it at the application in favour of portability 
}

resource "aws_apigatewayv2_stage" "public_api_prod" {
  api_id      = aws_apigatewayv2_api.public.id
  name        = "prod"
  auto_deploy = true
  tags        = local.resource_tags

  default_route_settings {
    throttling_rate_limit  = 100
    throttling_burst_limit = 200
  }

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway_public.arn
    format = jsonencode({
      requestId : "$context.requestId",
      ip : "$context.identity.sourceIp",
      requestTime : "$context.requestTime",
      httpMethod : "$context.httpMethod",
      routeKey : "$context.routeKey",
      status : "$context.status",
      protocol : "$context.protocol",
      responseLength : "$context.responseLength",
      authorizerStatus : "$context.authorizer.status",
      "authorizer.error" : "$context.authorizer.error",
      errorMessage : "$context.error.message",
      integrationErrorMessage : "$context.integrationErrorMessage",
      integrationStatus : "$context.integrationStatus",
      "integration.status" : "$context.integration.status",
      responseType : "$context.error.responseType",
    })
  }
}

# IAM permissions for the integration
data "aws_iam_policy_document" "apigateway_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["apigateway.amazonaws.com"]
    }
  }
}

# Authorizers
resource "aws_apigatewayv2_authorizer" "okta-jwt" {
  api_id           = aws_apigatewayv2_api.public.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "okta-jwt-authorizer"

  jwt_configuration {
    audience = var.jwt-audience
    issuer   = var.jwt-issuer
  }
}

###############################
# flask api integration + route
###############################
resource "aws_apigatewayv2_integration" "public_api" {
  api_id = aws_apigatewayv2_api.public.id

  integration_type       = "AWS_PROXY"
  connection_type        = "INTERNET"
  integration_method     = "POST"
  payload_format_version = "2.0"
  integration_uri        = aws_lambda_function.public_api.arn
  credentials_arn        = aws_iam_role.api_gateway_public_api.arn
  # Remove the stage name from the incoming requests
  request_parameters = {
    "overwrite:path" = "$request.path"
  }
}

resource "aws_apigatewayv2_route" "public_api_root" {
  api_id = aws_apigatewayv2_api.public.id
  # route_key = "ANY /{proxy+}"
  route_key          = "$default"
  target             = "integrations/${aws_apigatewayv2_integration.public_api.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.okta-jwt.id
}

# Need to leave the /OPTIONS requests as unauthenticated for CORS
# https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-cors.html
resource "aws_apigatewayv2_route" "public_api_root_options" {
  api_id    = aws_apigatewayv2_api.public.id
  route_key = "OPTIONS /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.public_api.id}"
}

resource "aws_iam_role" "api_gateway_public_api" {
  name               = "${var.project-name}-api-gateway-public_api"
  assume_role_policy = data.aws_iam_policy_document.apigateway_assume_role.json
  tags               = local.resource_tags
}

data "aws_iam_policy_document" "public_api_invoke" {
  # Lambda execution-related permissions
  statement {
    effect = "Allow"
    actions = [
      "lambda:InvokeFunction",
    ]
    resources = [
      aws_lambda_function.public_api.arn,
      "${aws_lambda_function.public_api.arn}:*",
    ]
  }
}

resource "aws_iam_role_policy" "api_gateway_invoke_public_api" {
  name   = "${var.project-name}-api-gateway-invoke-public_api"
  policy = data.aws_iam_policy_document.public_api_invoke.json
  role   = aws_iam_role.api_gateway_public_api.id
}
