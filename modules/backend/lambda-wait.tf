
locals {
  wait_lambda_handler    = "wait"
  wait_function_filename = "${path.module}/build/${local.wait_lambda_handler}.zip"
}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "wait_log_group" {
  name              = "/aws/lambda/${aws_lambda_function.wait_lambda.function_name}"
  retention_in_days = local.cloudwatch_log_retention
  tags              = local.resource_tags
}

# Lambda Role
resource "aws_iam_role" "iam_role_for_wait_lambda" {
  name               = "${var.project-name}-wait-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.resource_tags
}

# permissions for the Lambda role
data "aws_iam_policy_document" "wait_lambda_role_policy_document" {

  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["${aws_cloudwatch_log_group.wait_log_group.arn}:*"]
  }

  # StackSet-related permissions
  statement {
    effect = "Allow"
    actions = [
      "cloudformation:ListStackInstances",
      "cloudformation:ListStackSetOperations"
    ]
    resources = ["arn:aws:cloudformation:*:${var.account-primary}:stackset/${var.project-name}*:*"]
  }
}

resource "aws_iam_role_policy" "iam_role_policy_for_wait_lambda" {
  name   = "${var.project-name}-wait-lambda-policy"
  policy = data.aws_iam_policy_document.wait_lambda_role_policy_document.json
  role   = aws_iam_role.iam_role_for_wait_lambda.id
}

# Lambda Function
data "archive_file" "wait_function_package" {
  type        = "zip"
  output_path = local.wait_function_filename

  source {
    filename = "utils.py"
    content  = file("${local.lambda_path}/utils.py")
  }

  source {
    filename = "${local.wait_lambda_handler}.py"
    content  = file("${local.lambda_path}/${local.wait_lambda_handler}.py")
  }
}

resource "aws_lambda_function" "wait_lambda" {
  function_name    = "${var.project-name}-wait-function"
  role             = aws_iam_role.iam_role_for_wait_lambda.arn
  handler          = "${local.wait_lambda_handler}.handler"
  filename         = local.wait_function_filename
  source_code_hash = data.archive_file.wait_function_package.output_base64sha256
  runtime          = "python3.8"
  timeout          = 30
  depends_on       = [data.archive_file.wait_function_package]
  tags             = local.resource_tags
}
