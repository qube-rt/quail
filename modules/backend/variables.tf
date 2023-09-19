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

variable "notification-email" {
  type        = string
  description = "Email address from which notifications will be sent. Needs to be verified in SES."
}

variable "admin-email" {
  type        = string
  description = "Email address where email failure emails will be CCed to."
}

variable "admin-group-name" {
  type        = string
  description = "Name of the admins Okta group."
}

variable "cleanup-notice-notification-hours" {
  type        = list(number)
  default     = [12]
  description = "Controls how many advance notifications should be sent out before resources are cleaned up. E.g. [1,6,12] means the users will receive three warnings: 12, 6 and one hour before the resources get cleaned up."
}

variable "external-sns-failure-topic-arn" {
  type        = string
  default     = ""
  description = "If set, this topic will be notified of provisioning failures or lambda execution failures. If unset, a new topic will be created"
}

variable "support-localhost-urls" {
  type        = bool
  default     = false
  description = "Should Api Gateway cors policy and Cognito app support localhost URL. Used for development"
}

variable "hosting-domain" {
  type        = string
  description = "The domain where the application is going to be hosted, e.g. `www.quail.click`. It needs to have an ACM certificate associated with it."
}

variable "hosted-zone-name" {
  type        = string
  description = "The name of the hosted zone where the record will be added to point the `hosting-domain` to the Load Balancer, e.g. quail.click."
}

variable "cfn_data_bucket" {
  type        = string
  description = "The name of the bucket containing cfn templates and user data scripts."
}

variable "cross-account-role-name" {
  type        = string
  description = "The name of the role assumed by the APIs to carry out cross-account tasks"
}

variable "remote-accounts" {
  type        = list(string)
  description = "List of account IDs where users can provision instances (excl. the main account)."
  default     = []
}

variable "stack-set-execution-role-name" {
  type        = string
  description = "Name of the role assumed to create stack sets."
}

variable "instance-tags" {
  type = list(object({
    tag-name  = string,
    tag-value = string,
  }))
  default = [
    {
      tag-name : "user",
      tag-value : "$email"
    },
    {
      tag-name : "group",
      tag-value : "profile"
  }]
  description = "Tags to assign to the EC2 instances provisioned by end users. Values starting with $ will refer to the user's attributes."

  validation {
    condition     = length(var.instance-tags) == 2
    error_message = "You must have exactly two instance tags defined."
  }
}

variable "resource-tags" {
  type        = map(string)
  default     = {}
  description = "Tags to assign to resources provisioned by terraform. Apart from the listed tags, a {part_of: $${project-name}} tag is assigned to all resources."
}

variable "regional-data" {
  type = list(object({
    account-id   = string,
    region       = string,
    ssh-key-name = string,
    vpc-id       = string,
    subnet-id    = list(string),
  }))
  default     = []
  description = "Instance configuration dictionary. Os-type should be 'windows' or 'linux'"
}

variable "permission-data" {
  type = map(object({
    instance-types = list(string),
    operating-systems = list(object({
      name                = string,
      connection-protocol = string,
      template-filename   = string,
      user-data-file      = string,
      region-map = map(map(object({
        security-group        = string,
        instance-profile-name = string,
        ami                   = string,
      })))
    })),
    max-instance-count  = number,
    max-days-to-expiry  = number,
    max-extension-count = number,
  }))
  default     = {}
  description = "Allowed permission values for user groups."
}

variable "jwt-issuer" {
  type        = string
  description = "URL of the Auth Server issuing minting JWTs."
}

variable "jwt-audience" {
  type        = list(string)
  description = "Audiences to check the issued JWTs for."
}

variable "public-api-image-uri" {
  type        = string
  description = "ECR URI of the public API docker image."
}

variable "private-api-image-uri" {
  type        = string
  description = "ECR URI of the private API docker image."
}

variable "skip-resources-first-deployment" {
  type        = bool
  description = <<EOF
    Due to circular dependencies, some resources need to be skipped during
    the first deployment and recreated during the second deployment.
  EOF
}
