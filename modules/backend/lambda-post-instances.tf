
locals {
  post_instances_lambda_handler    = "post_instances"
  post_instances_function_filename = "${path.module}/build/${local.post_instances_lambda_handler}.zip"
}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "post_instances_log_group" {
  name              = "/aws/lambda/${aws_lambda_function.post_instances.function_name}"
  retention_in_days = local.cloudwatch_log_retention
  tags              = local.resource_tags
}

# Lambda Role
resource "aws_iam_role" "iam_role_for_post_instances_lambda" {
  name               = "${var.project-name}-post-instances-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.resource_tags
}

# permissions for the Lambda role
data "aws_iam_policy_document" "post_instances_lambda_role_policy_document" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["${aws_cloudwatch_log_group.post_instances_log_group.arn}:*"]
  }

  # DynamoDB-related permissions
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:GetItem"
    ]
    resources = [aws_dynamodb_table.permissions-table.arn]
  }
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
    resources = [aws_sfn_state_machine.provision_state_machine.arn]
  }
}

resource "aws_iam_role_policy" "iam_role_policy_for_post_instances_lambda" {
  name   = "${var.project-name}-post-instances-lambda-policy"
  policy = data.aws_iam_policy_document.post_instances_lambda_role_policy_document.json
  role   = aws_iam_role.iam_role_for_post_instances_lambda.id
}

# Lambda Function
data "archive_file" "post_instances_function_package" {
  type        = "zip"
  output_path = local.post_instances_function_filename

  source {
    filename = "utils.py"
    content  = file("${local.lambda_path}/utils.py")
  }

  source {
    filename = "${local.post_instances_lambda_handler}.py"
    content  = file("${local.lambda_path}/${local.post_instances_lambda_handler}.py")
  }
}

resource "aws_lambda_function" "post_instances" {
  function_name    = "${var.project-name}-post-instances-function"
  role             = aws_iam_role.iam_role_for_post_instances_lambda.arn
  handler          = "${local.post_instances_lambda_handler}.handler"
  filename         = local.post_instances_function_filename
  source_code_hash = data.archive_file.post_instances_function_package.output_base64sha256
  runtime          = "python3.8"
  timeout          = 30
  depends_on       = [data.archive_file.post_instances_function_package]
  tags             = local.resource_tags

  layers = [aws_lambda_layer_version.marshmallow_layer.arn]

  environment {
    variables = {
      "dynamodb_permissions_table_name" = aws_dynamodb_table.permissions-table.name
      "provision_sfn_arn"               = aws_sfn_state_machine.provision_state_machine.arn
      "dynamodb_state_table_name"       = aws_dynamodb_table.dynamodb-state-table.name
    }
  }
}
