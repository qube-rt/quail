# permissions to send emails via SES from the specified address
data "aws_iam_policy_document" "ses_notification_permissions" {
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
