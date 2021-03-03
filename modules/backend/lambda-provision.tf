
locals {
  provision_lambda_handler    = "provision"
  provision_function_filename = "${path.module}/build/${local.provision_lambda_handler}.zip"
}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "provision_log_group" {
  name              = "/aws/lambda/${aws_lambda_function.provision_lambda.function_name}"
  retention_in_days = local.cloudwatch_log_retention
  tags              = local.resource_tags
}

# Lambda Role
resource "aws_iam_role" "iam_role_for_provision_lambda" {
  name               = "${var.project-name}-provision-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.resource_tags
}

# permissions for the Lambda role
data "aws_iam_policy_document" "provision_lambda_role_policy_document" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["${aws_cloudwatch_log_group.provision_log_group.arn}:*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
    ]
    resources = ["arn:aws:s3:::${var.cfn_data_bucket}/*"]
  }

  # StackSet-related permissions
  statement {
    effect = "Allow"
    actions = [
      "cloudformation:CreateStackSet",
      "cloudformation:CreateStackInstances",
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "ec2:DescribeVpcs",
      "ec2:CreateSecurityGroup",
      "ec2:RunInstances",
      "ec2:DescribeKeyPairs",
      "ec2:AssociateIamInstanceProfile",
      "ec2:AuthorizeSecurityGroupIngress",
      "ec2:DescribeSecurityGroups",
      "ec2:DescribeInstances",
      "ec2:createTags"
    ]
    resources = ["*"]
  }

  ## DynamoDB permissions
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
    ]
    resources = [
      aws_dynamodb_table.permissions-table.arn,
      aws_dynamodb_table.dynamodb-regional-metadata-table.arn,
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
    ]
    resources = [aws_dynamodb_table.dynamodb-state-table.arn]
  }
}

resource "aws_iam_role_policy" "iam_role_policy_for_provision_lambda" {
  name   = "${var.project-name}-provision-lambda-policy"
  policy = data.aws_iam_policy_document.provision_lambda_role_policy_document.json
  role   = aws_iam_role.iam_role_for_provision_lambda.id
}

# Lambda Function
data "archive_file" "provision_function_package" {
  type        = "zip"
  output_path = local.provision_function_filename

  source {
    filename = "utils.py"
    content  = file("${local.lambda_path}/utils.py")
  }

  source {
    filename = "${local.provision_lambda_handler}.py"
    content  = file("${local.lambda_path}/${local.provision_lambda_handler}.py")
  }
}

resource "aws_lambda_function" "provision_lambda" {
  function_name    = "${var.project-name}-provision-function"
  role             = aws_iam_role.iam_role_for_provision_lambda.arn
  handler          = "${local.provision_lambda_handler}.handler"
  filename         = local.provision_function_filename
  source_code_hash = data.archive_file.provision_function_package.output_base64sha256
  runtime          = "python3.8"
  timeout          = 30
  depends_on       = [data.archive_file.provision_function_package]
  tags             = local.resource_tags

  environment {
    variables = {
      "project_name"                          = var.project-name
      "tag_config"                            = jsonencode(var.instance-tags)
      "dynamodb_regional_metadata_table_name" = aws_dynamodb_table.dynamodb-regional-metadata-table.name
      "dynamodb_state_table_name"             = aws_dynamodb_table.dynamodb-state-table.name
      "dynamodb_permissions_table_name"       = aws_dynamodb_table.permissions-table.name
      "cfn_data_bucket"                       = var.cfn_data_bucket
    }
  }
}
