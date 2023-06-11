variable "project-name" {
  type        = string
  default     = "quail"
  description = "Project name, used for resource naming"
}

variable "okta-groups" {
  type        = list(string)
  description = "The groups who should have permissions to use the application"
}
