
# Administrative Account Role
data "aws_iam_policy_document" "stackset_admin_account_role_policy_document" {

  statement {
    effect    = "Allow"
    actions   = ["sts:AssumeRole"]
    resources = ["arn:aws:iam::*:role/AWSCloudFormationStackSetExecutionRole"]
  }
}

data "aws_iam_policy_document" "stackset_admin_account_assume_role_policy_document" {

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type = "Service"
      identifiers = [
        "cloudformation.amazonaws.com",
        "cloudformation.ap-east-1.amazonaws.com"
      ]
    }
  }
}

resource "aws_iam_role" "stackset_admin_account_role" {
  name               = "AWSCloudFormationStackSetAdministrationRole"
  assume_role_policy = data.aws_iam_policy_document.stackset_admin_account_assume_role_policy_document.json
  tags               = local.resource_tags
}

resource "aws_iam_role_policy" "stackset_admin_account_role_policy" {
  name   = "${var.project-name}-AWSCloudFormationStackSetAdministrationRolePolicy"
  policy = data.aws_iam_policy_document.stackset_admin_account_role_policy_document.json
  role   = aws_iam_role.stackset_admin_account_role.id
}
