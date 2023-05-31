
locals {
  cleanup_scheduled_lambda_handler    = "cleanup_scheduled"
  cleanup_scheduled_function_filename = "${path.module}/build/${local.cleanup_scheduled_lambda_handler}.zip"
}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "cleanup_scheduled_log_group" {
  name              = "/aws/lambda/${aws_lambda_function.cleanup_scheduled_lambda.function_name}"
  retention_in_days = local.cloudwatch_log_retention
  tags              = local.resource_tags
}

# Lambda Role
resource "aws_iam_role" "iam_role_for_cleanup_scheduled_lambda" {
  name               = "${var.project-name}-cleanup-scheduled-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.resource_tags
}

# permissions for the Lambda role
data "aws_iam_policy_document" "cleanup_scheduled_lambda_role_policy_document" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["${aws_cloudwatch_log_group.cleanup_scheduled_log_group.arn}:*"]
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

  # DynamoDB-related permissions
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:Scan"
    ]
    resources = [aws_dynamodb_table.dynamodb-state-table.arn]
  }

  # SFN-related permissions
  statement {
    effect = "Allow"
    actions = [
      "states:StartExecution"
    ]
    resources = [aws_sfn_state_machine.cleanup_state_machine.arn]
  }

  # ses permissions
    statement {
    effect = "Allow"
    actions = [
      "ses:SendEmail",
    ]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "ses:FromAddress"

      values = [
        var.notification-email
      ]
    }
  }
}

resource "aws_iam_role_policy" "iam_role_policy_for_cleanup_scheduled_lambda" {
  name   = "${var.project-name}-cleanup-scheduled-lambda-policy"
  policy = data.aws_iam_policy_document.cleanup_scheduled_lambda_role_policy_document.json
  role   = aws_iam_role.iam_role_for_cleanup_scheduled_lambda.id
}

# Lambda Function
data "archive_file" "cleanup_scheduled_function_package" {
  type        = "zip"
  output_path = local.cleanup_scheduled_function_filename

  source {
    filename = "utils.py"
    content  = file("${local.lambda_path}/utils.py")
  }

  source {
    filename = "${local.cleanup_scheduled_lambda_handler}.py"
    content  = file("${local.lambda_path}/${local.cleanup_scheduled_lambda_handler}.py")
  }

  source {
    filename = "email_utils.py"
    content  = file("${local.lambda_path}/email_utils.py")
  }

  source {
    filename = "templates/cleanup_notice.txt"
    content  = file("${local.lambda_path}/templates/cleanup_notice.txt")
  }

  source {
    filename = "templates/cleanup_notice.html"
    content  = file("${local.lambda_path}/templates/cleanup_notice.html")
  }
}

resource "aws_lambda_function" "cleanup_scheduled_lambda" {
  function_name    = "${var.project-name}-cleanup-scheduled-function"
  role             = aws_iam_role.iam_role_for_cleanup_scheduled_lambda.arn
  handler          = "${local.cleanup_scheduled_lambda_handler}.handler"
  filename         = local.cleanup_scheduled_function_filename
  source_code_hash = data.archive_file.cleanup_scheduled_function_package.output_base64sha256
  runtime          = "python3.8"
  timeout          = 30
  depends_on       = [data.archive_file.cleanup_scheduled_function_package]
  tags             = local.resource_tags

  layers = [aws_lambda_layer_version.jinja_layer.arn]

  environment {
    variables = {
      "project_name"                      = var.project-name
      "dynamodb_state_table_name"         = aws_dynamodb_table.dynamodb-state-table.name
      "notification_email"                = var.notification-email
      "cleanup_notice_notification_hours" = jsonencode(var.cleanup-notice-notification-hours)
      "cleanup_sfn_arn"                   = aws_sfn_state_machine.cleanup_state_machine.arn
    }
  }
}

# schedule the every hour trigger
resource "aws_cloudwatch_event_rule" "every_hour" {
  name                = "every-hour"
  description         = "Fires every hour"
  schedule_expression = "rate(1 hour)"
  tags                = local.resource_tags
}

resource "aws_cloudwatch_event_target" "check_every_hour" {
  rule      = aws_cloudwatch_event_rule.every_hour.name
  target_id = "lambda"
  arn       = aws_lambda_function.cleanup_scheduled_lambda.arn
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_cleanup_scheduled_lambda" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cleanup_scheduled_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.every_hour.arn
}
