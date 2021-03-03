
locals {
  patch_instance_lambda_handler    = "patch_instance"
  patch_instance_function_filename = "${path.module}/build/${local.patch_instance_lambda_handler}.zip"
}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "patch_instance_log_group" {
  name              = "/aws/lambda/${aws_lambda_function.patch_instance.function_name}"
  retention_in_days = local.cloudwatch_log_retention
  tags              = local.resource_tags
}

# Lambda Role
resource "aws_iam_role" "iam_role_for_patch_instance_lambda" {
  name               = "${var.project-name}-patch-instance-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.resource_tags
}

# permissions for the Lambda role
data "aws_iam_policy_document" "patch_instance_lambda_role_policy_document" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["${aws_cloudwatch_log_group.patch_instance_log_group.arn}:*"]
  }

  # DynamoDB-related permissions
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
    ]
    resources = [
      aws_dynamodb_table.permissions-table.arn,
      aws_dynamodb_table.dynamodb-state-table.arn,
    ]
  }

  # StackSet-related permissions
  statement {
    effect = "Allow"
    actions = [
      "cloudformation:DescribeStackSet",
      "cloudformation:UpdateStackSet",
    ]
    resources = [
      "arn:aws:cloudformation:*:${var.account-primary}:stackset/${var.project-name}*:*"
    ]
  }
}

resource "aws_iam_role_policy" "iam_role_policy_for_patch_instance_lambda" {
  name   = "${var.project-name}-patch-instance-lambda-policy"
  policy = data.aws_iam_policy_document.patch_instance_lambda_role_policy_document.json
  role   = aws_iam_role.iam_role_for_patch_instance_lambda.id
}

# Lambda Function
data "archive_file" "patch_instance_function_package" {
  type        = "zip"
  output_path = local.patch_instance_function_filename

  source {
    filename = "utils.py"
    content  = file("${local.lambda_path}/utils.py")
  }

  source {
    filename = "${local.patch_instance_lambda_handler}.py"
    content  = file("${local.lambda_path}/${local.patch_instance_lambda_handler}.py")
  }
}

resource "aws_lambda_function" "patch_instance" {
  function_name    = "${var.project-name}-patch-instance-function"
  role             = aws_iam_role.iam_role_for_patch_instance_lambda.arn
  handler          = "${local.patch_instance_lambda_handler}.handler"
  filename         = local.patch_instance_function_filename
  source_code_hash = data.archive_file.patch_instance_function_package.output_base64sha256
  runtime          = "python3.8"
  timeout          = 30
  depends_on       = [data.archive_file.patch_instance_function_package]
  tags             = local.resource_tags

  layers = [aws_lambda_layer_version.marshmallow_layer.arn]

  environment {
    variables = {
      "dynamodb_state_table_name"       = aws_dynamodb_table.dynamodb-state-table.name
      "dynamodb_permissions_table_name" = aws_dynamodb_table.permissions-table.name
    }
  }
}
