# CloudWatch log group
resource "aws_cloudwatch_log_group" "api_gateway_prod" {
  name              = "/aws/gateway/${aws_apigatewayv2_api.main.name}/prod"
  retention_in_days = local.cloudwatch_log_retention
  tags              = local.resource_tags
}

# API Gateway + stage
resource "aws_apigatewayv2_api" "main" {
  name          = "${var.project-name}-http-api"
  protocol_type = "HTTP"
  tags          = local.resource_tags

  cors_configuration {
    allow_origins = [
      var.support-localhost-urls ? "http://localhost:3000" : "",
      "https://${var.hosting-domain}"
    ]
    allow_methods = [
      "*",
    ]
    allow_headers = [
      "*",
    ]
    expose_headers = [
      "*",
    ]
    allow_credentials = false
    max_age           = 30
  }
}

resource "aws_apigatewayv2_stage" "prod" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "prod"
  auto_deploy = true
  tags        = local.resource_tags

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway_prod.arn
    format          = "{ \"requestId\":\"$context.requestId\", \"ip\": \"$context.identity.sourceIp\", \"requestTime\":\"$context.requestTime\", \"httpMethod\":\"$context.httpMethod\",\"routeKey\":\"$context.routeKey\", \"status\":\"$context.status\",\"protocol\":\"$context.protocol\", \"responseLength\":\"$context.responseLength\", \"authorizerStatus\": \"$context.authorizer.status\" \"errorMessage\": \"$context.error.message\",  }"
  }
}

# Authorizers
resource "aws_apigatewayv2_authorizer" "cognito-jwt" {
  api_id           = aws_apigatewayv2_api.main.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "cognito-jwt-authorizer"

  jwt_configuration {
    audience = [aws_cognito_user_pool_client.main.id]
    issuer   = "https://cognito-idp.${var.region-primary}.amazonaws.com/${aws_cognito_user_pool_client.main.user_pool_id}"
  }
}

###################################
# Instance post integration + route
###################################
resource "aws_apigatewayv2_integration" "post_instances" {
  api_id = aws_apigatewayv2_api.main.id

  integration_type       = "AWS_PROXY"
  connection_type        = "INTERNET"
  integration_method     = "POST"
  payload_format_version = "2.0"
  integration_uri        = aws_lambda_function.post_instances.arn
  credentials_arn        = aws_iam_role.api_gateway_post_instances.arn
}

resource "aws_apigatewayv2_route" "instance_post" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /instance"
  target             = "integrations/${aws_apigatewayv2_integration.post_instances.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito-jwt.id
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

resource "aws_iam_role" "api_gateway_post_instances" {
  name               = "${var.project-name}-api-gateway-post-instances"
  assume_role_policy = data.aws_iam_policy_document.apigateway_assume_role.json
  tags               = local.resource_tags
}

# permissions for the Provision SFN state machine
data "aws_iam_policy_document" "post_instances_invoke" {
  # Lambda execution-related permissions
  statement {
    effect = "Allow"
    actions = [
      "lambda:InvokeFunction",
    ]
    resources = [
      aws_lambda_function.post_instances.arn,
      "${aws_lambda_function.post_instances.arn}:*",
    ]
  }
}

resource "aws_iam_role_policy" "api_gateway_post_instances" {
  name   = "${var.project-name}-api-gateway-post-instances"
  policy = data.aws_iam_policy_document.post_instances_invoke.json
  role   = aws_iam_role.api_gateway_post_instances.id
}

##################################
# instance get integration + route
##################################
resource "aws_apigatewayv2_integration" "get_instances" {
  api_id = aws_apigatewayv2_api.main.id

  integration_type       = "AWS_PROXY"
  connection_type        = "INTERNET"
  integration_method     = "POST"
  payload_format_version = "2.0"
  integration_uri        = aws_lambda_function.get_instances.arn
  credentials_arn        = aws_iam_role.api_gateway_get_instances.arn
}

resource "aws_apigatewayv2_route" "instance_get" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /instance"
  target             = "integrations/${aws_apigatewayv2_integration.get_instances.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito-jwt.id
}

resource "aws_iam_role" "api_gateway_get_instances" {
  name               = "${var.project-name}-api-gateway-get-instances"
  assume_role_policy = data.aws_iam_policy_document.apigateway_assume_role.json
  tags               = local.resource_tags
}

# permissions for the get instance route
data "aws_iam_policy_document" "get_instances_invoke" {
  # Lambda execution-related permissions
  statement {
    effect = "Allow"
    actions = [
      "lambda:InvokeFunction",
    ]
    resources = [
      aws_lambda_function.get_instances.arn,
      "${aws_lambda_function.get_instances.arn}:*",
    ]
  }
}

resource "aws_iam_role_policy" "api_gateway_invoke_get_instances" {
  name   = "${var.project-name}-api-gateway-invoke-get_instances"
  policy = data.aws_iam_policy_document.get_instances_invoke.json
  role   = aws_iam_role.api_gateway_get_instances.id
}

#####################################
# instance delete integration + route
#####################################
resource "aws_apigatewayv2_integration" "delete_instances" {
  api_id = aws_apigatewayv2_api.main.id

  integration_type       = "AWS_PROXY"
  connection_type        = "INTERNET"
  integration_method     = "POST"
  payload_format_version = "2.0"
  integration_uri        = aws_lambda_function.delete_instances.arn
  credentials_arn        = aws_iam_role.api_gateway_delete_instances.arn
}

resource "aws_apigatewayv2_route" "instance_delete" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "DELETE /instance/{id}"
  target             = "integrations/${aws_apigatewayv2_integration.delete_instances.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito-jwt.id
}

resource "aws_iam_role" "api_gateway_delete_instances" {
  name               = "${var.project-name}-api-gateway-delete-instances"
  assume_role_policy = data.aws_iam_policy_document.apigateway_assume_role.json
  tags               = local.resource_tags
}

# permissions for the get instance route
data "aws_iam_policy_document" "delete_instances_invoke" {
  # Lambda execution-related permissions
  statement {
    effect = "Allow"
    actions = [
      "lambda:InvokeFunction",
    ]
    resources = [
      aws_lambda_function.delete_instances.arn,
      "${aws_lambda_function.delete_instances.arn}:*",
    ]
  }
}

resource "aws_iam_role_policy" "api_gateway_invoke_delete_instances" {
  name   = "${var.project-name}-api-gateway-invoke-delete_instances"
  policy = data.aws_iam_policy_document.delete_instances_invoke.json
  role   = aws_iam_role.api_gateway_delete_instances.id
}

##########################################
# instance extend post integration + route
##########################################
resource "aws_apigatewayv2_integration" "post_instance_extend" {
  api_id = aws_apigatewayv2_api.main.id

  integration_type       = "AWS_PROXY"
  connection_type        = "INTERNET"
  integration_method     = "POST"
  payload_format_version = "2.0"
  integration_uri        = aws_lambda_function.post_instance_extend.arn
  credentials_arn        = aws_iam_role.api_gateway_post_instance_extend.arn
}

resource "aws_apigatewayv2_route" "instance_detail_extend" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /instance/{id}/extend"
  target             = "integrations/${aws_apigatewayv2_integration.post_instance_extend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito-jwt.id
}

resource "aws_iam_role" "api_gateway_post_instance_extend" {
  name               = "${var.project-name}-api-gateway-post-instance-extend"
  assume_role_policy = data.aws_iam_policy_document.apigateway_assume_role.json
  tags               = local.resource_tags
}

# permissions for the get instance route
data "aws_iam_policy_document" "post_instance_extend_invoke" {
  # Lambda execution-related permissions
  statement {
    effect = "Allow"
    actions = [
      "lambda:InvokeFunction",
    ]
    resources = [
      aws_lambda_function.post_instance_extend.arn,
      "${aws_lambda_function.post_instance_extend.arn}:*",
    ]
  }
}

resource "aws_iam_role_policy" "api_gateway_invoke_post_instance_extend" {
  name   = "${var.project-name}-api-gateway-invoke-post_instance_extend"
  policy = data.aws_iam_policy_document.post_instance_extend_invoke.json
  role   = aws_iam_role.api_gateway_post_instance_extend.id
}

##########################################
# instance stop post integration + route
##########################################
resource "aws_apigatewayv2_integration" "post_instance_stop" {
  api_id = aws_apigatewayv2_api.main.id

  integration_type       = "AWS_PROXY"
  connection_type        = "INTERNET"
  integration_method     = "POST"
  payload_format_version = "2.0"
  integration_uri        = aws_lambda_function.post_instance_stop.arn
  credentials_arn        = aws_iam_role.api_gateway_post_instance_stop.arn
}

resource "aws_apigatewayv2_route" "instance_detail_stop" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /instance/{id}/stop"
  target             = "integrations/${aws_apigatewayv2_integration.post_instance_stop.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito-jwt.id
}

resource "aws_iam_role" "api_gateway_post_instance_stop" {
  name               = "${var.project-name}-api-gateway-post-instance-stop"
  assume_role_policy = data.aws_iam_policy_document.apigateway_assume_role.json
  tags               = local.resource_tags
}

# permissions for the get instance route
data "aws_iam_policy_document" "post_instance_stop_invoke" {
  # Lambda execution-related permissions
  statement {
    effect = "Allow"
    actions = [
      "lambda:InvokeFunction",
    ]
    resources = [
      aws_lambda_function.post_instance_stop.arn,
      "${aws_lambda_function.post_instance_stop.arn}:*",
    ]
  }
}

resource "aws_iam_role_policy" "api_gateway_invoke_post_instance_stop" {
  name   = "${var.project-name}-api-gateway-invoke-post_instance_stop"
  policy = data.aws_iam_policy_document.post_instance_stop_invoke.json
  role   = aws_iam_role.api_gateway_post_instance_stop.id
}

##########################################
# instance start post integration + route
##########################################
resource "aws_apigatewayv2_integration" "post_instance_start" {
  api_id = aws_apigatewayv2_api.main.id

  integration_type       = "AWS_PROXY"
  connection_type        = "INTERNET"
  integration_method     = "POST"
  payload_format_version = "2.0"
  integration_uri        = aws_lambda_function.post_instance_start.arn
  credentials_arn        = aws_iam_role.api_gateway_post_instance_start.arn
}

resource "aws_apigatewayv2_route" "instance_detail_start" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /instance/{id}/start"
  target             = "integrations/${aws_apigatewayv2_integration.post_instance_start.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito-jwt.id
}

resource "aws_iam_role" "api_gateway_post_instance_start" {
  name               = "${var.project-name}-api-gateway-post-instance-start"
  assume_role_policy = data.aws_iam_policy_document.apigateway_assume_role.json
  tags               = local.resource_tags
}

# permissions for the get instance route
data "aws_iam_policy_document" "post_instance_start_invoke" {
  # Lambda execution-related permissions
  statement {
    effect = "Allow"
    actions = [
      "lambda:InvokeFunction",
    ]
    resources = [
      aws_lambda_function.post_instance_start.arn,
      "${aws_lambda_function.post_instance_start.arn}:*",
    ]
  }
}

resource "aws_iam_role_policy" "api_gateway_invoke_post_instance_start" {
  name   = "${var.project-name}-api-gateway-invoke-post_instance_start"
  policy = data.aws_iam_policy_document.post_instance_start_invoke.json
  role   = aws_iam_role.api_gateway_post_instance_start.id
}

####################################
# instance patch integration + route
####################################
resource "aws_apigatewayv2_integration" "patch_instance" {
  api_id = aws_apigatewayv2_api.main.id

  integration_type       = "AWS_PROXY"
  connection_type        = "INTERNET"
  integration_method     = "PATCH"
  payload_format_version = "2.0"
  integration_uri        = aws_lambda_function.patch_instance.arn
  credentials_arn        = aws_iam_role.api_gateway_patch_instance.arn
}

resource "aws_apigatewayv2_route" "instance_detail_patch" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "PATCH /instance/{id}"
  target             = "integrations/${aws_apigatewayv2_integration.patch_instance.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito-jwt.id
}

resource "aws_iam_role" "api_gateway_patch_instance" {
  name               = "${var.project-name}-api-gateway-patch_instance"
  assume_role_policy = data.aws_iam_policy_document.apigateway_assume_role.json
  tags               = local.resource_tags
}

# permissions for the get instance route
data "aws_iam_policy_document" "patch_instance_invoke" {
  # Lambda execution-related permissions
  statement {
    effect = "Allow"
    actions = [
      "lambda:InvokeFunction",
    ]
    resources = [
      aws_lambda_function.patch_instance.arn,
      "${aws_lambda_function.patch_instance.arn}:*",
    ]
  }
}

resource "aws_iam_role_policy" "api_gateway_invoke_patch_instance" {
  name   = "${var.project-name}-api-gateway-invoke-patch_instance"
  policy = data.aws_iam_policy_document.patch_instance_invoke.json
  role   = aws_iam_role.api_gateway_patch_instance.id
}

################################
# param get integration + route
################################
resource "aws_apigatewayv2_integration" "get_param" {
  api_id = aws_apigatewayv2_api.main.id

  integration_type       = "AWS_PROXY"
  connection_type        = "INTERNET"
  integration_method     = "POST"
  payload_format_version = "2.0"
  integration_uri        = aws_lambda_function.get_params.arn
  credentials_arn        = aws_iam_role.api_gateway_get_param.arn
}

resource "aws_apigatewayv2_route" "params_get" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /param"
  target             = "integrations/${aws_apigatewayv2_integration.get_param.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito-jwt.id
}

resource "aws_iam_role" "api_gateway_get_param" {
  name               = "${var.project-name}-api-gateway-get-params"
  assume_role_policy = data.aws_iam_policy_document.apigateway_assume_role.json
  tags               = local.resource_tags
}

# permissions for the get params route
data "aws_iam_policy_document" "get_param_invoke" {
  # Lambda execution-related permissions
  statement {
    effect = "Allow"
    actions = [
      "lambda:InvokeFunction",
    ]
    resources = [
      aws_lambda_function.get_params.arn,
      "${aws_lambda_function.get_params.arn}:*",
    ]
  }
}

resource "aws_iam_role_policy" "api_gateway_invoke_get_param" {
  name   = "${var.project-name}-api-gateway-invoke-get_param"
  policy = data.aws_iam_policy_document.get_param_invoke.json
  role   = aws_iam_role.api_gateway_get_param.id
}
