variable "project-name" {
  type        = string
  default     = "quail"
  description = "Project name, used for resource naming"
}

variable "admin-group-name" {
  type        = string
  description = "Name of the admins Okta group."
}
