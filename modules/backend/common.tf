locals {
  resource_tags = merge(
    {
      part_of = var.project-name
    },
    var.resource-tags
  )
  lambda_path              = "${path.module}/lambda-src"
  lambda_layer_path        = "${path.module}/lambda-layers"
  cloudwatch_log_retention = 0
  sns_error_topic_arn      = var.external-sns-failure-topic-arn == "" ? aws_sns_topic.error_topic[0].arn : var.external-sns-failure-topic-arn
}

# Shared IAM Assume role policy documents
data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "state_machine_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "ecs_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "ecs_tasks_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# Failure notification SNS topic
resource "aws_sns_topic" "error_topic" {
  count = var.external-sns-failure-topic-arn == "" ? 1 : 0
  name  = "${var.project-name}-error-topic"
  tags  = local.resource_tags
}
