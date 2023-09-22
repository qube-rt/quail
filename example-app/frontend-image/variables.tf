variable "profile" {
  type        = string
  default     = "default"
  description = "AWS configuration profile used with terraform for the main account"
}

variable "region-primary" {
  type        = string
  default     = "us-east-1"
  description = "AWS region where resources will be deployed"
}

variable "project-name" {
  type        = string
  default     = "quail"
  description = "Project name, used for resource naming"
}

variable "resource-tags" {
  type        = map(string)
  default     = {}
  description = "Tags to assign to resources provisioned by terraform. Apart from the listed tags, a {part_of: $${project-name}} tag is assigned to all resources."
}

variable "account-name-labels" {
  type        = map(string)
  default     = {}
  description = "Mapping of AWS account IDs to user friendly names."
}

variable "group-name-labels" {
  type        = map(string)
  default     = {}
  description = "Mapping of Okta group names to user friendly names."
}

variable "api-root-url" {
  type        = string
  description = "Base URL of the public API"
}

variable "oauth_app_client_id" {
  type        = string
  description = "ID of the OAuth app used for authentication"
}

variable "auth_server_issuer" {
  type        = string
  description = "JWT Token issuer"
}
