
# Administrative Account Role
data "aws_iam_policy_document" "stackset_admin_role" {

  statement {
    effect    = "Allow"
    actions   = ["sts:AssumeRole"]
    resources = ["arn:aws:iam::*:role/${var.stack-set-execution-role-name}"]
  }
}

data "aws_iam_policy_document" "stackset_admin_assume_role" {

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

resource "aws_iam_role" "stackset_admin_role" {
  name               = "${var.project-name}-StackSetAdministrationRole"
  assume_role_policy = data.aws_iam_policy_document.stackset_admin_assume_role.json
  tags               = local.resource_tags
}

resource "aws_iam_role_policy" "stackset_admin_role_policy" {
  name   = "${var.project-name}-StackSetAdministrationRolePolicy"
  policy = data.aws_iam_policy_document.stackset_admin_role.json
  role   = aws_iam_role.stackset_admin_role.id
}
