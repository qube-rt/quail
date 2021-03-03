
locals {
  post_instance_extend_lambda_handler    = "post_instance_extend"
  post_instance_extend_function_filename = "${path.module}/build/${local.post_instance_extend_lambda_handler}.zip"
}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "post_instance_extend_log_group" {
  name              = "/aws/lambda/${aws_lambda_function.post_instance_extend.function_name}"
  retention_in_days = local.cloudwatch_log_retention
  tags              = local.resource_tags
}

# Lambda Role
resource "aws_iam_role" "iam_role_for_post_instance_extend_lambda" {
  name               = "${var.project-name}-post-instance-extend-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.resource_tags
}

# permissions for the Lambda role
data "aws_iam_policy_document" "post_instance_extend_lambda_role_policy_document" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["${aws_cloudwatch_log_group.post_instance_extend_log_group.arn}:*"]
  }

  # DynamoDB-related permissions
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:UpdateItem"
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

}

resource "aws_iam_role_policy" "iam_role_policy_for_post_instance_extend_lambda" {
  name   = "${var.project-name}-post-instance-extend-lambda-policy"
  policy = data.aws_iam_policy_document.post_instance_extend_lambda_role_policy_document.json
  role   = aws_iam_role.iam_role_for_post_instance_extend_lambda.id
}

# Lambda Function
data "archive_file" "post_instance_extend_function_package" {
  type        = "zip"
  output_path = local.post_instance_extend_function_filename

  source {
    filename = "utils.py"
    content  = file("${local.lambda_path}/utils.py")
  }

  source {
    filename = "${local.post_instance_extend_lambda_handler}.py"
    content  = file("${local.lambda_path}/${local.post_instance_extend_lambda_handler}.py")
  }
}

resource "aws_lambda_function" "post_instance_extend" {
  function_name    = "${var.project-name}-post-instance-extend-function"
  role             = aws_iam_role.iam_role_for_post_instance_extend_lambda.arn
  handler          = "${local.post_instance_extend_lambda_handler}.handler"
  filename         = local.post_instance_extend_function_filename
  source_code_hash = data.archive_file.post_instance_extend_function_package.output_base64sha256
  runtime          = "python3.8"
  timeout          = 30
  depends_on       = [data.archive_file.post_instance_extend_function_package]
  tags             = local.resource_tags

  layers = [aws_lambda_layer_version.marshmallow_layer.arn]

  environment {
    variables = {
      "dynamodb_state_table_name"       = aws_dynamodb_table.dynamodb-state-table.name
      "dynamodb_permissions_table_name" = aws_dynamodb_table.permissions-table.name
    }
  }
}
