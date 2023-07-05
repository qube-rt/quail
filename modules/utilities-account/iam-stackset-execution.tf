
# Execution account role
data "aws_iam_policy_document" "stackset_execution_role" {
  statement {
    effect    = "Allow"
    actions   = ["*"]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "stackset_execution_role_trust_relationship" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${var.account-primary}:root"]
    }
  }
}

resource "aws_iam_role" "stackset_execution_role" {
  name               = "AWSCloudFormationStackSetExecutionRole"
  assume_role_policy = data.aws_iam_policy_document.stackset_execution_role_trust_relationship.json
  tags               = local.resource_tags
}

resource "aws_iam_role_policy" "stackset_execution_role" {
  name   = "${var.project-name}-StacksetExecuteRolePolicy"
  policy = data.aws_iam_policy_document.stackset_execution_role.json
  role   = aws_iam_role.stackset_execution_role.id
}
