
locals {
  get_params_lambda_handler    = "get_params"
  get_params_function_filename = "${path.module}/build/${local.get_params_lambda_handler}.zip"
}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "get_params_log_group" {
  name              = "/aws/lambda/${aws_lambda_function.get_params.function_name}"
  retention_in_days = local.cloudwatch_log_retention
  tags              = local.resource_tags
}

# Lambda Role
resource "aws_iam_role" "iam_role_for_get_params_lambda" {
  name               = "${var.project-name}-get-params-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.resource_tags
}

# permissions for the Lambda role
data "aws_iam_policy_document" "get_params_lambda_role_policy_document" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["${aws_cloudwatch_log_group.get_params_log_group.arn}:*"]
  }

  # DynamoDB-related permissions
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:GetItem"
    ]
    resources = [aws_dynamodb_table.permissions-table.arn]
  }
}

resource "aws_iam_role_policy" "iam_role_policy_for_get_params_lambda" {
  name   = "${var.project-name}-get-params-lambda-policy"
  policy = data.aws_iam_policy_document.get_params_lambda_role_policy_document.json
  role   = aws_iam_role.iam_role_for_get_params_lambda.id
}

# Lambda Function
data "archive_file" "get_params_function_package" {
  type        = "zip"
  output_path = local.get_params_function_filename

  source {
    filename = "utils.py"
    content  = file("${local.lambda_path}/utils.py")
  }

  source {
    filename = "${local.get_params_lambda_handler}.py"
    content  = file("${local.lambda_path}/${local.get_params_lambda_handler}.py")
  }
}

resource "aws_lambda_function" "get_params" {
  function_name    = "${var.project-name}-get-params-function"
  role             = aws_iam_role.iam_role_for_get_params_lambda.arn
  handler          = "${local.get_params_lambda_handler}.handler"
  filename         = local.get_params_function_filename
  source_code_hash = data.archive_file.get_params_function_package.output_base64sha256
  runtime          = "python3.8"
  timeout          = 30
  depends_on       = [data.archive_file.get_params_function_package]
  tags             = local.resource_tags

  environment {
    variables = {
      "dynamodb_permissions_table_name" = aws_dynamodb_table.permissions-table.name
    }
  }
}
