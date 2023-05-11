# CloudWatch log group
resource "aws_cloudwatch_log_group" "public_api" {
  name              = "/aws/lambda/${local.ecr_image_name}"
  retention_in_days = local.cloudwatch_log_retention
  tags              = local.resource_tags
}

# Lambda Role
resource "aws_iam_role" "public_api" {
  name               = "${local.ecr_image_name}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.resource_tags
}

# permissions for the Lambda role
data "aws_iam_policy_document" "public_api" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:CreateLogGroup",
      "logs:PutLogEvents"
    ]
    resources = ["${aws_cloudwatch_log_group.public_api.arn}:*"]
  }

  # DynamoDB-related permissions
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:Scan",
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
      "ec2:StopInstances",
    ]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "ec2:ResourceTag/part_of"

      values = [var.project-name]
    }
  }

  # SFN-related permissions
  statement {
    effect = "Allow"
    actions = [
      "states:StartExecution"
    ]
    resources = [aws_sfn_state_machine.provision_state_machine.arn,
    aws_sfn_state_machine.cleanup_state_machine.arn]
  }
}

resource "aws_iam_role_policy" "public_api" {
  name   = "${local.ecr_image_name}--lambda-policy"
  policy = data.aws_iam_policy_document.public_api.json
  role   = aws_iam_role.public_api.id
}

data "aws_ecr_image" "public_api" {
  repository_name = local.ecr_image_name
  image_tag       = "latest"

  depends_on = [null_resource.public_api_image_publish]
}


resource "aws_lambda_function" "public_api" {
  function_name = local.ecr_image_name
  role          = aws_iam_role.public_api.arn
  timeout       = 30
  memory_size   = 512
  tags          = local.resource_tags

  package_type = "Image"
  image_uri    = "${aws_ecr_repository.public_api.repository_url}@${data.aws_ecr_image.public_api.id}"

  depends_on = [docker_image.public_api, null_resource.public_api_image_publish]

  environment {
    variables = {
      "DYNAMODB_PERMISSIONS_TABLE_NAME" = aws_dynamodb_table.permissions-table.name
      "DYNAMODB_STATE_TABLE_NAME"       = aws_dynamodb_table.dynamodb-state-table.name
      "PROVISION_SFN_ARN"               = aws_sfn_state_machine.provision_state_machine.arn
      "CLEANUP_SFN_ARN"                 = aws_sfn_state_machine.cleanup_state_machine.arn
      "FLASK_DEBUG"                     = 1
      "FLASK_ENV"                       = "development"
      "GUNICORN_WORKERS"                = 1
      "LOG_LEVEL"                       = "debug"
      "SECRET_KEY"                      = "not-so-secret"
      "AWS_LWA_READINESS_CHECK_PATH"    = "/healthcheck"
    }
  }
}
