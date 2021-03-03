resource "aws_iam_instance_profile" "application_profile" {
  name_prefix = "${var.project-name}-instance-profile"
  role        = aws_iam_role.instance_profile_role.name
}

resource "aws_iam_role" "instance_profile_role" {
  name_prefix = "${var.project-name}-instance-profile"

  assume_role_policy = <<-EOF
  {
      "Version": "2012-10-17",
      "Statement": [
          {
              "Action": "sts:AssumeRole",
              "Principal": {
                "Service": "ec2.amazonaws.com"
              },
              "Effect": "Allow",
              "Sid": ""
          }
      ]
  }
  EOF

  tags = local.resource_tags
}

data "aws_iam_policy_document" "instance_profile_policy" {
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "iam_role_policy_for_cleanup_scheduled_lambda" {
  role        = aws_iam_role.instance_profile_role.id
  name_prefix = "${var.project-name}-cleanup-scheduled-lambda-policy"
  policy      = data.aws_iam_policy_document.instance_profile_policy.json
}

resource "aws_iam_role_policy_attachment" "rds_read_only_policy" {
  role       = aws_iam_role.instance_profile_role.id
  policy_arn = "arn:aws:iam::aws:policy/AmazonRDSReadOnlyAccess"
}
