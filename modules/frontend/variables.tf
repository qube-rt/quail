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

# React configuration variables
variable "api-root-url" {
  type        = string
  description = "Root URL of the application API."
}

variable "cognito-domain" {
  type        = string
  description = "Domain of the Cognito user pool."
}

variable "cognito-client-id" {
  type        = string
  description = "ID of the Cognito client used for authentication."
}

variable "logout-url" {
  type        = string
  description = "The user will be redirected there when logging out from the application."
}
