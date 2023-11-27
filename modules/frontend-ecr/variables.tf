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

variable "npm_registry_url" {
  type        = string
  default     = "https://registry.npmjs.org"
  description = "URL for alternative NPM registry to obtain remote packages"
}

variable "admin-group-name" {
  type        = string
  default     = "quail-admins"
  description = "Name of the admins Okta group."
}

variable "account-name-labels" {
  type        = map(string)
  default     = {}
  description = "Mapping of AWS account IDs to user friendly names."
}

variable "region-name-labels" {
  type = map(string)
  default = {
    "us-east-1"      = "US East (N. Virginia)",
    "us-east-2"      = "US East (Ohio)",
    "us-west-1"      = "US West (N. California)",
    "us-west-2"      = "US West (Oregon)",
    "af-south-1"     = "Africa (Cape Town)",
    "ap-east-1"      = "Asia Pacific (Hong Kong)",
    "ap-south-1"     = "Asia Pacific (Mumbai)",
    "ap-southeast-1" = "Asia Pacific (Singapore)",
    "ap-southeast-2" = "Asia Pacific (Sydney)",
    "ap-northeast-1" = "Asia Pacific (Tokyo)",
    "ap-northeast-2" = "Asia Pacific (Seoul)",
    "ap-northeast-3" = "Asia Pacific (Osaka-Local)",
    "ca-central-1"   = "Canada (Central)",
    "eu-central-1"   = "Europe (Frankfurt)",
    "eu-west-1"      = "Europe (Ireland)",
    "eu-west-2"      = "Europe (London)",
    "eu-west-3"      = "Europe (Paris)",
    "eu-south-1"     = "Europe (Milan)",
    "eu-north-1"     = "Europe (Stockholm)",
    "me-south-1"     = "Middle East (Bahrain)",
    "sa-east-1"      = "South America (São Paulo)",
  }
  description = "Mapping of AWS EC2 region names to user friendly names."
}

variable "instance-name-labels" {
  type = map(string)
  default = {
    "t3.nano"  = "t3.nano (2vCPU/0.5GB)",
    "t3.micro" = "t3.micro (2vCPU/1GB)",
    "t3.small" = "t3.small (2vCPU/2GB)",
  }
  description = "Mapping of AWS EC2 Instance types to user friendly names."
}

variable "group-name-labels" {
  type        = map(string)
  default     = {}
  description = "Mapping of Okta group names to user friendly names."
}
