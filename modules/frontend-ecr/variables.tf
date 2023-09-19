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

variable "jwt-issuer" {
  type        = string
  description = "URL of the Auth Server issuing minting JWTs."
}

variable "jwt-client-id" {
  type        = string
  description = "ID of the OAuth client App."
}

variable "account-name-labels" {
  type        = map(string)
  default     = {}
  description = "Mapping of AWS account IDs to user friendly names."
}

variable "npm_registry_url" {
  type        = string
  default     = "https://registry.npmjs.org"
  description = "URL for alternative NPM registry to obtain remote packages"
}
