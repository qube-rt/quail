# Using a data source to avoid dependency cycles
data "aws_sfn_state_machine" "cleanup_sfn" {
  count = var.skip-resources-first-deployment ? 0 : 1
  name  = local.cleanup_sfn_name
}

data "aws_sfn_state_machine" "provision_sfn" {
  count = var.skip-resources-first-deployment ? 0 : 1
  name  = local.provision_sfn_name
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
  # Base lambda permissions
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:CreateLogGroup",
      "logs:PutLogEvents"
    ]
    resources = ["${aws_cloudwatch_log_group.private_api.arn}:*"]
  }

  # Permission to use the StackSet admin role
  statement {
    effect = "Allow"
    actions = [
      "iam:GetRole",
      "iam:PassRole"
    ]
    resources = [aws_iam_role.stackset_admin_role.arn]
  }

  # Permissions to assume roles in remote accounts
  statement {
    effect = "Allow"
    actions = [
      "sts:AssumeRole",
    ]
    resources = [
      for account_id in var.remote-accounts : "arn:aws:iam::${account_id}:role/${var.cross-account-role-name}"
    ]
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
      "dynamodb:DeleteItem", "dynamodb:Scan"
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
  dynamic "statement" {
    for_each = data.aws_sfn_state_machine.cleanup_sfn

    content {
      effect = "Allow"
      actions = [
        "states:StartExecution",
        "states:SendTaskSuccess",
        "states:SendTaskFailure",
      ]
      resources = [data.aws_sfn_state_machine.cleanup_sfn[0].arn]
    }
  }

  dynamic "statement" {
    for_each = data.aws_sfn_state_machine.cleanup_sfn

    content {
      effect = "Allow"
      actions = [
        "states:SendTaskSuccess",
        "states:SendTaskFailure",
      ]
      resources = [data.aws_sfn_state_machine.provision_sfn[0].arn]
    }
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
  name   = "${local.ecr_private_api_name}-lambda-policy"
  policy = data.aws_iam_policy_document.private_api.json
  role   = aws_iam_role.private_api.id
}

resource "random_password" "private_api_secret_key" {
  length = 24
}

resource "aws_lambda_function" "private_api" {
  function_name = local.ecr_private_api_name
  role          = aws_iam_role.private_api.arn
  timeout       = 30
  memory_size   = 512
  tags          = local.resource_tags

  package_type = "Image"
  image_uri    = var.private-api-image-uri

  environment {
    variables = {
      "PROJECT_NAME" = var.project-name
      "TAG_CONFIG"   = jsonencode(var.instance-tags)

      "DYNAMODB_PERMISSIONS_TABLE_NAME"       = aws_dynamodb_table.permissions-table.name
      "DYNAMODB_STATE_TABLE_NAME"             = aws_dynamodb_table.dynamodb-state-table.name
      "DYNAMODB_REGIONAL_METADATA_TABLE_NAME" = aws_dynamodb_table.dynamodb-regional-metadata-table.name

      # Fetching the SFNs ARN indirectly to avoid dependency cycles
      "PROVISION_SFN_ARN" = (var.skip-resources-first-deployment ?
        "Unset skip-resources-first-deployment to fix this." :
        data.aws_sfn_state_machine.provision_sfn[0].arn
      )
      "CLEANUP_SFN_ARN" = (var.skip-resources-first-deployment ?
        "Unset skip-resources-first-deployment to fix this." :
        data.aws_sfn_state_machine.cleanup_sfn[0].arn
      )
      "CROSS_ACCOUNT_ROLE_NAME" = var.cross-account-role-name
      "CFN_DATA_BUCKET"         = var.cfn_data_bucket

      "NOTIFICATION_EMAIL"                = var.notification-email
      "ADMIN_EMAIL"                       = var.admin-email
      "ADMIN_GROUP_NAME"                  = var.admin-group-name
      "SNS_ERROR_TOPIC_ARN"               = local.sns_error_topic_arn
      "CLEANUP_NOTICE_NOTIFICATION_HOURS" = jsonencode(var.cleanup-notice-notification-hours)
      "STACK_SET_EXECUTION_ROLE_NAME"     = var.stack-set-execution-role-name
      "STACK_SET_ADMIN_ROLE_ARN"          = aws_iam_role.stackset_admin_role.arn

      "FLASK_DEBUG"                  = local.quail-api-debug
      "FLASK_ENV"                    = local.quail-api-env
      "GUNICORN_WORKERS"             = 1
      "LOG_LEVEL"                    = local.quail-api-log-level
      "SECRET_KEY"                   = random_password.private_api_secret_key.result
      "AWS_LWA_READINESS_CHECK_PATH" = "/healthcheck"
    }
  }
}
