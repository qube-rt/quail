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

variable "http_proxy" {
  type        = string
  default     = ""
  description = "Sets http_proxy environment variable during docker build. Useful for airgapped environments that require a proxy."
}

variable "https_proxy" {
  type        = string
  default     = ""
  description = "Sets https_proxy environment variable during docker build. Useful for airgapped environments that require a proxy."
}

variable "no_proxy" {
  type        = string
  default     = ""
  description = "Sets no_proxy environment variable during docker build. Useful for airgapped environments that require a proxy."
}

variable "pip_index_url" {
  type        = string
  default     = "https://pypi.python.org/simple"
  description = "Optional base URL for PyPI that pip uses to fetch python packages during docker build."
}
