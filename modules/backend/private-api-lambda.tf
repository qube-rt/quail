# Using a data source to avoid dependency cycles
data "aws_sfn_state_machine" "cleanup_state_machine" {
  name     = "${var.project-name}-cleanup-state-machine"
}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "private_api" {
  name              = "/aws/lambda/${local.ecr_private_api_name}"
  retention_in_days = local.cloudwatch_log_retention
  tags              = local.resource_tags
}

# Lambda Role
resource "aws_iam_role" "private_api" {
  name               = "${local.ecr_private_api_name}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.resource_tags
}

# permissions for the Lambda role
data "aws_iam_policy_document" "private_api" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:CreateLogGroup",
      "logs:PutLogEvents"
    ]
    resources = ["${aws_cloudwatch_log_group.private_api.arn}:*"]
  }

  # S3 permissions
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
      "cloudformation:ListStackInstances",
      "cloudformation:ListStackSetOperations",
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
      "arn:aws:cloudformation:*:${var.account-primary}:stack/StackSet-${var.project-name}*:*",
      "arn:aws:cloudformation:*:${var.account-primary}:stackset/${var.project-name}*:*"
    ]
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
      "dynamodb:GetItem",
            "dynamodb:DeleteItem",
    ]
    resources = [aws_dynamodb_table.dynamodb-state-table.arn]
  }


  # Allow publishing to the error SNS topic
  statement {
    effect = "Allow"
    actions = [
      "sns:Publish"
    ]
    resources = [local.sns_error_topic_arn]
  }

  # SFN-related permissions
  statement {
    effect = "Allow"
    actions = [
      "states:StartExecution",
      "states:SendTaskSuccess",
      "states:SendTaskFailure",
    ]
    resources = [data.aws_sfn_state_machine.cleanup_state_machine.arn]
  }

  statement {
    effect = "Allow"
    actions = [
      "states:SendTaskSuccess",
      "states:SendTaskFailure",
    ]
    resources = [aws_sfn_state_machine.provision_state_machine.arn]
  }

  # SES Permissions
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

resource "aws_iam_role_policy" "private_api" {
  name   = "${local.ecr_private_api_name}--lambda-policy"
  policy = data.aws_iam_policy_document.private_api.json
  role   = aws_iam_role.private_api.id
}

data "aws_ecr_image" "private_api" {
  repository_name = local.ecr_private_api_name
  image_tag       = "latest"

  depends_on = [null_resource.private_api_image_publish]
}


resource "aws_lambda_function" "private_api" {
  function_name = local.ecr_private_api_name
  role          = aws_iam_role.private_api.arn
  timeout       = 30
  memory_size   = 512
  tags          = local.resource_tags

  package_type = "Image"
  image_uri    = "${aws_ecr_repository.private_api.repository_url}@${data.aws_ecr_image.private_api.id}"

  depends_on = [docker_image.private_api, null_resource.private_api_image_publish]

  environment {
    variables = {
      "PROJECT_NAME"                          = var.project-name
      "DYNAMODB_PERMISSIONS_TABLE_NAME"       = aws_dynamodb_table.permissions-table.name
      "DYNAMODB_STATE_TABLE_NAME"             = aws_dynamodb_table.dynamodb-state-table.name
      "DYNAMODB_REGIONAL_METADATA_TABLE_NAME" = aws_dynamodb_table.dynamodb-regional-metadata-table.name
      "TAG_CONFIG"                            = jsonencode(var.instance-tags)
      "CFN_DATA_BUCKET"                       = var.cfn_data_bucket

      "NOTIFICATION_EMAIL"  = var.notification-email
      "ADMIN_EMAIL"         = var.admin-email
      "SNS_ERROR_TOPIC_ARN" = local.sns_error_topic_arn
      "CLEANUP_SFN_ARN"     = data.aws_sfn_state_machine.cleanup_state_machine.arn

      "FLASK_DEBUG"                  = 1
      "FLASK_ENV"                    = "development"
      "GUNICORN_WORKERS"             = 1
      "LOG_LEVEL"                    = "debug"
      "SECRET_KEY"                   = "not-so-secret"
      "AWS_LWA_READINESS_CHECK_PATH" = "/healthcheck"
    }
  }
}
