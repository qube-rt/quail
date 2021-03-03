
locals {
  post_instance_start_lambda_handler    = "post_instance_start"
  post_instance_start_function_filename = "${path.module}/build/${local.post_instance_start_lambda_handler}.zip"
}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "post_instance_start_log_group" {
  name              = "/aws/lambda/${aws_lambda_function.post_instance_start.function_name}"
  retention_in_days = local.cloudwatch_log_retention
  tags              = local.resource_tags
}

# Lambda Role
resource "aws_iam_role" "iam_role_for_post_instance_start_lambda" {
  name               = "${var.project-name}-post-instance-start-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.resource_tags
}

# permissions for the Lambda role
data "aws_iam_policy_document" "post_instance_start_lambda_role_policy_document" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["${aws_cloudwatch_log_group.post_instance_start_log_group.arn}:*"]
  }

  # DynamoDB-related permissions
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
    ]
    resources = [aws_dynamodb_table.dynamodb-state-table.arn]
  }

  # StackSet-related permissions
  statement {
    effect = "Allow"
    actions = [
      "cloudformation:ListStackInstances",
    ]
    resources = [
      "arn:aws:cloudformation:*:${var.account-primary}:stackset/${var.project-name}*:*"
    ]
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


  # EC2-related permissions
  statement {
    effect = "Allow"
    actions = [
      "ec2:DescribeInstances",
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "ec2:StartInstances",
    ]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "ec2:ResourceTag/part_of"

      values = [var.project-name]
    }
  }
}

resource "aws_iam_role_policy" "iam_role_policy_for_post_instance_start_lambda" {
  name   = "${var.project-name}-post-instance-start-lambda-policy"
  policy = data.aws_iam_policy_document.post_instance_start_lambda_role_policy_document.json
  role   = aws_iam_role.iam_role_for_post_instance_start_lambda.id
}

# Lambda Function
data "archive_file" "post_instance_start_function_package" {
  type        = "zip"
  output_path = local.post_instance_start_function_filename

  source {
    filename = "utils.py"
    content  = file("${local.lambda_path}/utils.py")
  }

  source {
    filename = "${local.post_instance_start_lambda_handler}.py"
    content  = file("${local.lambda_path}/${local.post_instance_start_lambda_handler}.py")
  }
}

resource "aws_lambda_function" "post_instance_start" {
  function_name    = "${var.project-name}-post-instance-start-function"
  role             = aws_iam_role.iam_role_for_post_instance_start_lambda.arn
  handler          = "${local.post_instance_start_lambda_handler}.handler"
  filename         = local.post_instance_start_function_filename
  source_code_hash = data.archive_file.post_instance_start_function_package.output_base64sha256
  runtime          = "python3.8"
  timeout          = 30
  depends_on       = [data.archive_file.post_instance_start_function_package]
  tags             = local.resource_tags

  environment {
    variables = {
      "dynamodb_state_table_name" = aws_dynamodb_table.dynamodb-state-table.name
    }
  }
}
