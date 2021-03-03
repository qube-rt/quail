variable "region-primary" {
  type        = string
  description = "AWS region where resources will be deployed"
}

variable "account-primary" {
  type        = string
  description = "AWS account where resources will be deployed"
}

variable "project-name" {
  type        = string
  description = "Project name, used for resource naming"
}

variable "resource-tags" {
  type        = map(string)
  default     = {}
  description = "Tags to assign to resources provisioned by terraform. Apart from the listed tags, a {part_of: $${project-name}} tag is assigned to all resources."
}

# ECS service configuration variables
variable "ecr-repository-url" {
  type        = string
  description = "The name of the ECR image serving the application's UI."
}

variable "ecr-container-name" {
  type        = string
  description = "The url of the image in ECR."
}

variable "hosting-domain" {
  type        = string
  description = "The domain where the application is going to be hosted, e.g. `www.quail.click`. It needs to have an ACM certificate associated with it."
}

variable "hosted-zone-name" {
  type        = string
  description = "The name of the hosted zone where the record will be added to point the `hosting-domain` to the Load Balancer, e.g. quail.click."
}
