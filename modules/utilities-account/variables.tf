variable "project-name" {
  type        = string
  description = "Project name, used for resource naming"
}

variable "account-primary" {
  type        = string
  description = "AWS account hosting the infrastructure and the stacksets"
}

variable "user-data-bucket" {
  type        = string
  description = "ARN of the bucket storing user data"
}

variable "cross-account-role-name" {
  type        = string
  description = "The name of the role assumed by the APIs to carry out cross-account tasks"
}

variable "cross-account-principals" {
  type        = list(string)
  description = "List of AWS Principals to assume the cross-account role"
}

variable "resource-tags" {
  type        = map(string)
  default     = {}
  description = "Tags to assign to resources provisioned by terraform. Apart from the listed tags, a {part_of: $${project-name}} tag is assigned to all resources."
}
