
locals {
  get_instances_lambda_handler    = "get_instances"
  get_instances_function_filename = "${path.module}/build/${local.get_instances_lambda_handler}.zip"
}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "get_instances_log_group" {
  name              = "/aws/lambda/${aws_lambda_function.get_instances.function_name}"
  retention_in_days = local.cloudwatch_log_retention
  tags              = local.resource_tags
}

# Lambda Role
resource "aws_iam_role" "iam_role_for_get_instances_lambda" {
  name               = "${var.project-name}-get-instances-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.resource_tags
}

# permissions for the Lambda role
data "aws_iam_policy_document" "get_instances_lambda_role_policy_document" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["${aws_cloudwatch_log_group.get_instances_log_group.arn}:*"]
  }

  # DynamoDB-related permissions
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:Scan"
    ]
    resources = [aws_dynamodb_table.dynamodb-state-table.arn]
  }
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:GetItem"
    ]
    resources = [aws_dynamodb_table.permissions-table.arn]
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
}

resource "aws_iam_role_policy" "iam_role_policy_for_get_instances_lambda" {
  name   = "${var.project-name}-get-instances-lambda-policy"
  policy = data.aws_iam_policy_document.get_instances_lambda_role_policy_document.json
  role   = aws_iam_role.iam_role_for_get_instances_lambda.id
}

# Lambda Function
data "archive_file" "get_instances_function_package" {
  type        = "zip"
  output_path = local.get_instances_function_filename

  source {
    filename = "utils.py"
    content  = file("${local.lambda_path}/utils.py")
  }

  source {
    filename = "${local.get_instances_lambda_handler}.py"
    content  = file("${local.lambda_path}/${local.get_instances_lambda_handler}.py")
  }
}

resource "aws_lambda_function" "get_instances" {
  function_name    = "${var.project-name}-get-instances-function"
  role             = aws_iam_role.iam_role_for_get_instances_lambda.arn
  handler          = "${local.get_instances_lambda_handler}.handler"
  filename         = local.get_instances_function_filename
  source_code_hash = data.archive_file.get_instances_function_package.output_base64sha256
  runtime          = "python3.8"
  timeout          = 30
  depends_on       = [data.archive_file.get_instances_function_package]
  tags             = local.resource_tags

  environment {
    variables = {
      "dynamodb_state_table_name"       = aws_dynamodb_table.dynamodb-state-table.name
      "dynamodb_permissions_table_name" = aws_dynamodb_table.permissions-table.name
    }
  }
}
