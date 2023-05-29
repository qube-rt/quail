# CloudWatch log group
resource "aws_cloudwatch_log_group" "provision_state_machine_log_group" {
  name              = "/aws/states/${var.project-name}/${aws_sfn_state_machine.provision_state_machine.name}"
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
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
      "logs:DescribeLogGroups"
    ]
    resources = ["*"]
    # resources = [aws_cloudwatch_log_group.provision_state_machine_log_group.arn]
  }

  # Lambda permissions
  statement {
    effect = "Allow"
    actions = [
      "lambda:InvokeFunction",
    ]
    resources = [
      aws_lambda_function.provision_lambda.arn,
      "${aws_lambda_function.provision_lambda.arn}:*",
      aws_lambda_function.wait_lambda.arn,
      "${aws_lambda_function.wait_lambda.arn}:*",
      aws_lambda_function.notify_success_lambda.arn,
      "${aws_lambda_function.notify_success_lambda.arn}:*",
      aws_lambda_function.notify_failure_lambda.arn,
      "${aws_lambda_function.notify_failure_lambda.arn}:*",
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

  name     = "${var.project-name}-provision-state-machine"
  role_arn = aws_iam_role.iam_role_for_provision_state_machine.arn

  definition = jsonencode({
    "Comment" : "A instance provisioning workflow",
    "StartAt" : "Provision",
    "States" : {
      "Provision" : {
        "Type" : "Task",
        "Resource" : "arn:aws:states:::lambda:invoke",
        "Parameters" : {
          "FunctionName" : "${aws_lambda_function.provision_lambda.arn}:$LATEST",
          "Payload" : {
            "Input.$" : "$"
          }
        },
        "Next" : "Wait"
      },
      "Wait" : {
        "Type" : "Task",
        "Resource" : "arn:aws:states:::lambda:invoke",
        "Parameters" : {
          "FunctionName" : "${aws_lambda_function.wait_lambda.arn}:$LATEST",
          "Payload" : {
            "stackset_id.$" : "$.Payload.stackset_id",
            "stackset_email.$" : "$.Payload.stackset_email",
            "error_if_no_operations" : true
          }
        },
        "ResultPath" : null,
        "Next" : "Notify Success",
        "Retry" : [
          {
            "ErrorEquals" : [
              "StackSetExecutionInProgressException"
            ],
            "IntervalSeconds" : 30,
            "BackoffRate" : 1,
            "MaxAttempts" : 40
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
        "Resource" : "arn:aws:states:::lambda:invoke",
        "Parameters" : {
          "FunctionName" : "${aws_lambda_function.notify_success_lambda.arn}:$LATEST",
          "Payload" : {
            "stackset_id.$" : "$.Payload.stackset_id",
            "stackset_email.$" : "$.Payload.stackset_email"
          }
        },
        "End" : true
      },
      "Notify Failure" : {
        "Type" : "Task",
        "Resource" : "arn:aws:states:::lambda:invoke",
        "Parameters" : {
          "FunctionName" : "${aws_lambda_function.notify_failure_lambda.arn}:$LATEST",
          "Payload" : {
            "stackset_id.$" : "$.Payload.stackset_id",
            "stackset_email.$" : "$.Payload.stackset_email"
          }
        },
        "End" : true
      }
    }
  })
}
