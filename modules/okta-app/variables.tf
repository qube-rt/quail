variable "project-name" {
  type        = string
  default     = "quail"
  description = "Project name, used for resource naming"
}

variable "okta-groups" {
  type        = list(string)
  description = "The groups who should have permissions to use the application"
}

variable "support-localhost-urls" {
  type        = bool
  default     = false
  description = "Should the Okta app support localhost URL for login/logout. Used for development"
}

variable "hosting-domain" {
  type        = string
  description = "The domain where the application is going to be hosted, e.g. `www.quail.click`. It needs to have an ACM certificate associated with it."
}
