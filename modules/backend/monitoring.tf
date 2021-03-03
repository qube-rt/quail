# Alerts for Provision SFN
resource "aws_cloudwatch_metric_alarm" "provision_sfn_failed" {
  alarm_name = "${var.project-name}-provision-sfn-executions-failed"

  namespace           = "AWS/States"
  metric_name         = "ExecutionsFailed"
  statistic           = "Sum"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  datapoints_to_alarm = 1
  evaluation_periods  = 1
  period              = 300
  dimensions = {
    "StateMachineArn" = aws_sfn_state_machine.provision_state_machine.arn
  }
  treat_missing_data = "notBreaching"

  actions_enabled = true
  alarm_actions   = [local.sns_error_topic_arn]

  tags = local.resource_tags
}

resource "aws_cloudwatch_metric_alarm" "provision_sfn_aborted" {
  alarm_name = "${var.project-name}-provision-sfn-executions-aborted"

  namespace           = "AWS/States"
  metric_name         = "ExecutionsAborted"
  statistic           = "Sum"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  datapoints_to_alarm = 1
  evaluation_periods  = 1
  period              = 300
  dimensions = {
    "StateMachineArn" = aws_sfn_state_machine.provision_state_machine.arn
  }
  treat_missing_data = "notBreaching"

  actions_enabled = true
  alarm_actions   = [local.sns_error_topic_arn]

  tags = local.resource_tags
}

resource "aws_cloudwatch_metric_alarm" "provision_sfn_throttled" {
  alarm_name = "${var.project-name}-provision-sfn-executions-throttled"

  namespace           = "AWS/States"
  metric_name         = "ExecutionsThrottled"
  statistic           = "Sum"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  datapoints_to_alarm = 1
  evaluation_periods  = 1
  period              = 300
  dimensions = {
    "StateMachineArn" = aws_sfn_state_machine.provision_state_machine.arn
  }
  treat_missing_data = "notBreaching"

  actions_enabled = true
  alarm_actions   = [local.sns_error_topic_arn]

  tags = local.resource_tags
}

# Alerts for Cleanup SFN
resource "aws_cloudwatch_metric_alarm" "cleanup_sfn_failed" {
  alarm_name = "${var.project-name}-cleanup-sfn-executions-failed"

  namespace           = "AWS/States"
  metric_name         = "ExecutionsFailed"
  statistic           = "Sum"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  datapoints_to_alarm = 1
  evaluation_periods  = 1
  period              = 300
  dimensions = {
    "StateMachineArn" = aws_sfn_state_machine.cleanup_state_machine.arn
  }
  treat_missing_data = "notBreaching"

  actions_enabled = true
  alarm_actions   = [local.sns_error_topic_arn]

  tags = local.resource_tags
}

resource "aws_cloudwatch_metric_alarm" "cleanup_sfn_aborted" {
  alarm_name = "${var.project-name}-cleanup-sfn-executions-aborted"

  namespace           = "AWS/States"
  metric_name         = "ExecutionsAborted"
  statistic           = "Sum"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  datapoints_to_alarm = 1
  evaluation_periods  = 1
  period              = 300
  dimensions = {
    "StateMachineArn" = aws_sfn_state_machine.cleanup_state_machine.arn
  }
  treat_missing_data = "notBreaching"

  actions_enabled = true
  alarm_actions   = [local.sns_error_topic_arn]

  tags = local.resource_tags
}

resource "aws_cloudwatch_metric_alarm" "cleanup_sfn_throttled" {
  alarm_name = "${var.project-name}-cleanup-sfn-executions-throttled"

  namespace           = "AWS/States"
  metric_name         = "ExecutionsThrottled"
  statistic           = "Sum"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  datapoints_to_alarm = 1
  evaluation_periods  = 1
  period              = 300
  dimensions = {
    "StateMachineArn" = aws_sfn_state_machine.cleanup_state_machine.arn
  }
  treat_missing_data = "notBreaching"

  actions_enabled = true
  alarm_actions   = [local.sns_error_topic_arn]

  tags = local.resource_tags
}

# Lambda functions not covered by state machines or API Gateway
resource "aws_cloudwatch_metric_alarm" "cleanup_scheduled_error" {
  alarm_name = "${var.project-name}-cleanup-scheduled-lambda-error"

  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  statistic           = "Sum"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  datapoints_to_alarm = 1
  evaluation_periods  = 1
  period              = 300
  dimensions = {
    "FunctionName" = aws_lambda_function.cleanup_scheduled_lambda.function_name
  }
  treat_missing_data = "notBreaching"

  actions_enabled = true
  alarm_actions   = [local.sns_error_topic_arn]

  tags = local.resource_tags
}

# API Gateway errors
resource "aws_cloudwatch_metric_alarm" "api_gateway_5xx_response" {
  alarm_name = "${var.project-name}-api-5xx-responses"

  namespace           = "AWS/ApiGateway"
  metric_name         = "5xx"
  statistic           = "Sum"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  datapoints_to_alarm = 1
  evaluation_periods  = 1
  period              = 300
  dimensions = {
    "ApiId" = aws_apigatewayv2_api.main.id
  }
  treat_missing_data = "notBreaching"

  actions_enabled = true
  alarm_actions   = [local.sns_error_topic_arn]

  tags = local.resource_tags
}
