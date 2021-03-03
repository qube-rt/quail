
locals {
  cleanup_instances_lambda_handler    = "cleanup_instances"
  cleanup_instances_function_filename = "${path.module}/build/${local.cleanup_instances_lambda_handler}.zip"
}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "cleanup_instances_log_group" {
  name              = "/aws/lambda/${aws_lambda_function.cleanup_instances_lambda.function_name}"
  retention_in_days = local.cloudwatch_log_retention
  tags              = local.resource_tags
}

# Lambda Role
resource "aws_iam_role" "iam_role_for_cleanup_instances_lambda" {
  name               = "${var.project-name}-cleanup-instances-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.resource_tags
}

# permissions for the Lambda role
data "aws_iam_policy_document" "cleanup_instances_lambda_role_policy_document" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["${aws_cloudwatch_log_group.cleanup_instances_log_group.arn}:*"]
  }

  # StackSet-related permissions
  statement {
    effect = "Allow"
    actions = [
      "cloudformation:ListStackInstances",
      "cloudformation:DeleteStackInstances",
    ]
    resources = [
      "arn:aws:cloudformation:*:${var.account-primary}:stackset/${var.project-name}*:*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "cloudformation:DescribeStacks",
      "cloudformation:DeleteStackSet"
    ]
    resources = [
      "arn:aws:cloudformation:*:${var.account-primary}:stack/StackSet-${var.project-name}*",
      "arn:aws:cloudformation:*:${var.account-primary}:stack/StackSet-${var.project-name}*:*"
    ]
  }

  # StackSet-related permissions
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:DeleteItem",
      "dynamodb:Scan"
    ]
    resources = [aws_dynamodb_table.dynamodb-state-table.arn]
  }
}

resource "aws_iam_role_policy" "iam_role_policy_for_cleanup_instances_lambda" {
  name   = "${var.project-name}-cleanup-instances-lambda-policy"
  policy = data.aws_iam_policy_document.cleanup_instances_lambda_role_policy_document.json
  role   = aws_iam_role.iam_role_for_cleanup_instances_lambda.id
}

resource "aws_iam_role_policy" "ses_policy_for_cleanup_instances_lambda" {
  name   = "${var.project-name}-cleanup-instances-lambda-policy-for-ses"
  policy = data.aws_iam_policy_document.ses_notification_permissions.json
  role   = aws_iam_role.iam_role_for_cleanup_instances_lambda.id
}

# Lambda Function
data "archive_file" "cleanup_instances_function_package" {
  type        = "zip"
  output_path = local.cleanup_instances_function_filename

  source {
    filename = "utils.py"
    content  = file("${local.lambda_path}/utils.py")
  }

  source {
    filename = "${local.cleanup_instances_lambda_handler}.py"
    content  = file("${local.lambda_path}/${local.cleanup_instances_lambda_handler}.py")
  }

  source {
    filename = "email_utils.py"
    content  = file("${local.lambda_path}/email_utils.py")
  }

  source {
    filename = "templates/cleanup_complete.txt"
    content  = file("${local.lambda_path}/templates/cleanup_complete.txt")
  }

  source {
    filename = "templates/cleanup_complete.html"
    content  = file("${local.lambda_path}/templates/cleanup_complete.html")
  }
}

resource "aws_lambda_function" "cleanup_instances_lambda" {
  function_name    = "${var.project-name}-cleanup-instances-function"
  role             = aws_iam_role.iam_role_for_cleanup_instances_lambda.arn
  handler          = "${local.cleanup_instances_lambda_handler}.handler"
  filename         = local.cleanup_instances_function_filename
  source_code_hash = data.archive_file.cleanup_instances_function_package.output_base64sha256
  runtime          = "python3.8"
  timeout          = 30
  depends_on       = [data.archive_file.cleanup_instances_function_package]
  tags             = local.resource_tags

  layers = [aws_lambda_layer_version.jinja_layer.arn]

  environment {
    variables = {
      "project_name"       = var.project-name
      "notification_email" = var.notification-email
    }
  }
}