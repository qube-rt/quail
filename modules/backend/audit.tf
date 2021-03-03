resource "aws_cloudwatch_dashboard" "audit" {
  dashboard_name = "${var.project-name}-audit"

  dashboard_body = jsonencode(
    {
      "widgets" : [
        {
          "type" : "log",
          "x" : 0,
          "y" : 0,
          "width" : 24,
          "height" : 18,
          "properties" : {
            "query" : "SOURCE '/aws/lambda/quail-cleanup-complete-function' | SOURCE '/aws/lambda/quail-cleanup-instances-function' | SOURCE '/aws/lambda/quail-cleanup-scheduled-function' | SOURCE '/aws/lambda/quail-delete-instances-function' | SOURCE '/aws/lambda/quail-get-instances-function' | SOURCE '/aws/lambda/quail-get-params-function' | SOURCE '/aws/lambda/quail-notify-failure-function' | SOURCE '/aws/lambda/quail-notify-success-function' | SOURCE '/aws/lambda/quail-patch-instance-function' | SOURCE '/aws/lambda/quail-post-instance-extend-function' | SOURCE '/aws/lambda/quail-post-instance-start-function' | SOURCE '/aws/lambda/quail-post-instance-stop-function' | SOURCE '/aws/lambda/quail-post-instances-function' | SOURCE '/aws/lambda/quail-provision-function' | fields @timestamp, @message\n| filter audit=1 \n| sort @timestamp desc\n| limit 200",
            "region" : var.region-primary,
            "stacked" : false,
            "view" : "table",
            "title" : "Audit trail from lambda log groups"
          }
        }
      ]
    }
  )
}
