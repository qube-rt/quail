variable "region-primary" {
  type        = string
  description = "AWS region where resources will be deployed"
}

variable "account-primary" {
  type        = string
  description = "AWS account hosting the infrastructure and the stacksets"
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
