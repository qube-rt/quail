resource "aws_iam_role" "cross_account_role" {
  name = var.cross-account-role-name

  assume_role_policy = <<-EOF
  {
      "Version": "2012-10-17",
      "Statement": [
          {
              "Action": "sts:AssumeRole",
              "Principal": {
                "AWS": ${jsonencode(var.cross-account-principals)}
              },
              "Effect": "Allow",
              "Sid": ""
          }
      ]
  }
  EOF

  tags = local.resource_tags
}

data "aws_iam_policy_document" "cross_account_role" {
  statement {
    effect = "Allow"
    actions = [
      "cloudformation:DescribeStacks",
    ]
    resources = [
      "*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "ec2:DescribeInstances",
    ]
    resources = [
      "*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "ec2:StopInstances",
      "ec2:StartInstances"
    ]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "ec2:ResourceTag/part_of"

      values = [var.project-name]
    }
  }
}

resource "aws_iam_role_policy" "cross_account_role" {
  role        = aws_iam_role.cross_account_role.id
  name_prefix = "${var.project-name}-cross-account-permissions"
  policy      = data.aws_iam_policy_document.cross_account_role.json
}
