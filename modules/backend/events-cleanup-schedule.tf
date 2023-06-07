# Trigger every hour
resource "aws_cloudwatch_event_rule" "every_hour" {
  name        = "every-hour"
  description = "Fires every hour"
  schedule_expression = "rate(1 hour)"
  tags                = local.resource_tags
}

resource "aws_cloudwatch_event_target" "check_every_hour" {
  rule      = aws_cloudwatch_event_rule.every_hour.name
  target_id = "lambda"
  arn       = aws_lambda_function.private_api.arn

  input = jsonencode({
    "resourcePath" : "/cleanupSchedule",
    "path" : "/cleanupSchedule",
    "httpMethod" : "POST",
  })
}

resource "aws_lambda_permission" "cloudwatch_invoke_private_api" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.private_api.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.every_hour.arn
}
