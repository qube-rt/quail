
locals {
  notify_failure_lambda_handler    = "notify_failure"
  notify_failure_function_filename = "${path.module}/build/${local.notify_failure_lambda_handler}.zip"
}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "notify_failure_log_group" {
  name              = "/aws/lambda/${aws_lambda_function.notify_failure_lambda.function_name}"
  retention_in_days = local.cloudwatch_log_retention
  tags              = local.resource_tags
}

# Lambda Role
resource "aws_iam_role" "iam_role_for_notify_failure_lambda" {
  name               = "${var.project-name}-notify-failure-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.resource_tags
}

# permissions for the Lambda role
data "aws_iam_policy_document" "notify_failure_lambda_role_policy_document" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["${aws_cloudwatch_log_group.notify_failure_log_group.arn}:*"]
  }

  # Allow publishing to the error SNS topic
  statement {
    effect = "Allow"
    actions = [
      "sns:Publish"
    ]
    resources = [local.sns_error_topic_arn]
  }

  # StackSet-related permissions
  statement {
    effect = "Allow"
    actions = [
      "cloudformation:ListStackInstances",
    ]
    resources = ["arn:aws:cloudformation:*:${var.account-primary}:stackset/${var.project-name}*:*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "cloudformation:DescribeStacks",
    ]
    resources = [
      "arn:aws:cloudformation:*:${var.account-primary}:stack/StackSet-${var.project-name}*",
      "arn:aws:cloudformation:*:${var.account-primary}:stack/StackSet-${var.project-name}*:*"
    ]
  }

  # SFN-related permissions
  statement {
    effect = "Allow"
    actions = [
      "states:StartExecution"
    ]
    resources = [aws_sfn_state_machine.cleanup_state_machine.arn]
  }
}

resource "aws_iam_role_policy" "iam_role_policy_for_notify_failure_lambda" {
  name   = "${var.project-name}-notify-failure-lambda-policy"
  policy = data.aws_iam_policy_document.notify_failure_lambda_role_policy_document.json
  role   = aws_iam_role.iam_role_for_notify_failure_lambda.id
}

resource "aws_iam_role_policy" "ses_policy_for_notify_failure_lambda" {
  name   = "${var.project-name}-notify-failure-lambda-policy-for-ses"
  policy = data.aws_iam_policy_document.ses_notification_permissions.json
  role   = aws_iam_role.iam_role_for_notify_failure_lambda.id
}

# Lambda Function
data "archive_file" "notify_failure_function_package" {
  type        = "zip"
  output_path = local.notify_failure_function_filename

  source {
    filename = "utils.py"
    content  = file("${local.lambda_path}/utils.py")
  }

  source {
    filename = "${local.notify_failure_lambda_handler}.py"
    content  = file("${local.lambda_path}/${local.notify_failure_lambda_handler}.py")
  }

  source {
    filename = "email_utils.py"
    content  = file("${local.lambda_path}/email_utils.py")
  }

  source {
    filename = "templates/provision_failure.txt"
    content  = file("${local.lambda_path}/templates/provision_failure.txt")
  }

  source {
    filename = "templates/provision_failure.html"
    content  = file("${local.lambda_path}/templates/provision_failure.html")
  }
}

resource "aws_lambda_function" "notify_failure_lambda" {
  function_name    = "${var.project-name}-notify-failure-function"
  role             = aws_iam_role.iam_role_for_notify_failure_lambda.arn
  handler          = "${local.notify_failure_lambda_handler}.handler"
  filename         = local.notify_failure_function_filename
  source_code_hash = data.archive_file.notify_failure_function_package.output_base64sha256
  runtime          = "python3.8"
  timeout          = 30
  depends_on       = [data.archive_file.notify_failure_function_package]
  tags             = local.resource_tags

  layers = [aws_lambda_layer_version.jinja_layer.arn]

  environment {
    variables = {
      "project_name"        = var.project-name
      "notification_email"  = var.notification-email
      "admin_email"         = var.admin-email
      "sns_error_topic_arn" = local.sns_error_topic_arn
      "cleanup_sfn_arn"     = aws_sfn_state_machine.cleanup_state_machine.arn
    }
  }
}
