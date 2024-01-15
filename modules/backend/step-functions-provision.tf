locals {
  provision_sfn_name    = "${var.project-name}-provision-state-machine"
  provision_retry_delay = 30
}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "provision_state_machine_log_group" {
  name              = "/aws/states/${var.project-name}/${local.provision_sfn_name}"
  retention_in_days = local.cloudwatch_log_retention
  tags              = local.resource_tags
}

# Step Machine Role
resource "aws_iam_role" "iam_role_for_provision_state_machine" {
  name               = "${var.project-name}-provision-state-machine-role"
  assume_role_policy = data.aws_iam_policy_document.state_machine_assume_role.json
  tags               = local.resource_tags
}

# permissions for the Step Machine role
data "aws_iam_policy_document" "provision_state_machine_role_policy_document" {

  # Cloudwatch Permissions
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogDelivery",
      "logs:CreateLogStream",
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutLogEvents",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
      "logs:DescribeLogGroups"
    ]
    resources = ["*"]
  }

  # Lambda permissions
  statement {
    effect = "Allow"
    actions = [
      "lambda:InvokeFunction",
    ]
    resources = [
      aws_lambda_function.private_api.arn,
      "${aws_lambda_function.private_api.arn}:*",
    ]
  }
}

resource "aws_iam_role_policy" "iam_role_policy_for_provision_state_machine" {
  name   = "${var.project-name}-provision-state-machine-policy"
  policy = data.aws_iam_policy_document.provision_state_machine_role_policy_document.json
  role   = aws_iam_role.iam_role_for_provision_state_machine.id
}


# SFN State Machine
resource "aws_sfn_state_machine" "provision_state_machine" {
  tags = local.resource_tags

  name     = local.provision_sfn_name
  role_arn = aws_iam_role.iam_role_for_provision_state_machine.arn

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.provision_state_machine_log_group.arn}:*"
    include_execution_data = true
    level                  = "ERROR"
  }

  definition = jsonencode({
    "Comment" : "A instance provisioning workflow",
    "StartAt" : "Provision",
    "States" : {
      "Provision" : {
        "Type" : "Task",
        "Resource" : "arn:aws:states:::lambda:invoke.waitForTaskToken",
        "TimeoutSeconds" : 300,
        "HeartbeatSeconds" : 60,
        "Parameters" : {
          "FunctionName" : "${aws_lambda_function.private_api.arn}:$LATEST",
          "Payload" : {
            "resourcePath" : "/provision",
            "path" : "/provision",
            "headers" : {
              "Content-Type" : "application/json",
              "TaskToken.$" : "$$.Task.Token"
            },
            "httpMethod" : "POST",
            "body.$" : "States.JsonToString($)"
          },
        },
        "Next" : "Wait"
      },
      "Wait" : {
        "Type" : "Task",
        "Resource" : "arn:aws:states:::lambda:invoke.waitForTaskToken",
        "TimeoutSeconds" : 1800,
        "HeartbeatSeconds" : 40,
        "Parameters" : {
          "FunctionName" : "${aws_lambda_function.private_api.arn}:$LATEST",
          "Payload" : {
            "resourcePath" : "/wait",
            "path" : "/wait",
            "httpMethod" : "GET",
            "headers" : {
              "Content-Type" : "application/json",
              "TaskToken.$" : "$$.Task.Token"
            },
            "queryStringParameters" : {
              "stackset_email.$" : "$.stackset_email",
              "stackset_id.$" : "$..stackset_id",
              "operation_id.$" : "$.operation_id"
            }
          }
        },
        "ResultPath" : null,
        "Next" : "Notify Success",
        "Retry" : [
          {
            "ErrorEquals" : [
              "StackSetExecutionInProgressException"
            ],
            "IntervalSeconds" : local.provision_retry_delay,
            "BackoffRate" : 1,
            "MaxAttempts" : floor(var.provision-timeout / local.provision_retry_delay) + 1
          }
        ],
        "Catch" : [
          {
            "ErrorEquals" : [
              "StackSetExecutionInProgressException"
            ],
            "ResultPath" : null,
            "Next" : "Notify Failure"
          }
        ]
      },
      "Notify Success" : {
        "Type" : "Task",
        "Resource" : "arn:aws:states:::lambda:invoke.waitForTaskToken",
        "HeartbeatSeconds" : 30,
        "Parameters" : {
          "FunctionName" : "${aws_lambda_function.private_api.arn}:$LATEST",
          "Payload" : {
            "resourcePath" : "/notifySuccess",
            "path" : "/notifySuccess",
            "headers" : {
              "Content-Type" : "application/json",
              "TaskToken.$" : "$$.Task.Token"
            },
            "httpMethod" : "POST",
            "body.$" : "States.JsonToString($)"
          },
        },
        "End" : true
      },
      "Notify Failure" : {
        "Type" : "Task",
        "Resource" : "arn:aws:states:::lambda:invoke.waitForTaskToken",
        "HeartbeatSeconds" : 30,
        "Parameters" : {
          "FunctionName" : "${aws_lambda_function.private_api.arn}:$LATEST",
          "Payload" : {
            "resourcePath" : "/notifyFailure",
            "path" : "/notifyFailure",
            "headers" : {
              "Content-Type" : "application/json",
              "TaskToken.$" : "$$.Task.Token"
            },
            "httpMethod" : "POST",
            "body.$" : "States.JsonToString($)"
          },
        },
        "End" : true
      }
    }
  })
}
