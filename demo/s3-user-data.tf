locals {
  resource_tags = merge(
    {
      part_of = var.project-name
    },
    var.resource-tags
  )
}

resource "aws_s3_bucket" "cfn_data_bucket" {
  bucket = "${var.project-name}-cfn-data-bucket"
  tags   = local.resource_tags
}

# Note - TF Destroy does not remove the ACL
resource "aws_s3_bucket_acl" "cfn_data_bucket_acl" {
  bucket = aws_s3_bucket.cfn_data_bucket.id
  acl    = "private"
}

resource "aws_s3_bucket_policy" "allow_access_from_remote_accounts" {
  bucket = aws_s3_bucket.cfn_data_bucket.id
  policy = data.aws_iam_policy_document.allow_access_from_remote_accounts.json
}

data "aws_iam_policy_document" "allow_access_from_remote_accounts" {
  statement {
    principals {
      type = "AWS"
      identifiers = [
        module.utilities-account-second.instance-profile-role-arn
      ]
    }

    actions = [
      "s3:GetObject",
    ]

    resources = [
      "${aws_s3_bucket.cfn_data_bucket.arn}/*",
    ]
  }
}

# User data files
resource "aws_s3_object" "user_data_file" {
  bucket = aws_s3_bucket.cfn_data_bucket.bucket
  key    = each.key
  source = each.value
  etag   = filemd5(each.key)

  for_each = fileset("", "${path.root}/user-data/*")
}

resource "aws_s3_object" "cfn_template_file" {
  bucket = aws_s3_bucket.cfn_data_bucket.bucket
  key    = each.key
  source = each.value
  etag   = filemd5(each.key)

  for_each = fileset("", "${path.root}/cfn-templates/*")
}
