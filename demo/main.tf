locals {
  regional-data = {
    eu-west-1 = {
      ssh-key-name = module.utilities-regional-primary.ssh-key-name,
      vpc-id       = module.utilities-regional-primary.vpc-id,
      subnet-id    = module.utilities-regional-primary.subnet-ids,
    },
    us-east-1 = {
      ssh-key-name = module.utilities-regional-secondary.ssh-key-name,
      vpc-id       = module.utilities-regional-secondary.vpc-id,
      subnet-id    = module.utilities-regional-secondary.subnet-ids,
    },
  }

  permission-data = {
    quail-developers = {
      instance-types = ["t3.nano", "t3.micro", "t3.small"],
      operating-systems = [
        {
          name                  = "AWS Linux 2",
          connection-protocol   = "ssh",
          instance-profile-name = module.utilities-global.instance-profile-name,
          template-filename     = "cfn-templates/aws_linux.yaml",
          user-data-file        = "user-data/linux.sh",
          region-map = {
            eu-west-1 = {
              security-group = module.utilities-regional-primary.security-group-id,
              ami            = "ami-0bb3fad3c0286ebd5"
            }
            us-east-1 = {
              security-group = module.utilities-regional-secondary.security-group-id,
              ami            = "ami-09te47d2ba12ee1ff75"
            }
          }
        },
        {
          name                  = "Ubuntu 20.04",
          connection-protocol   = "ssh",
          instance-profile-name = module.utilities-global.instance-profile-name,
          template-filename     = "cfn-templates/ubuntu_2004.yaml",
          user-data-file        = "user-data/linux.sh",
          region-map = {
            eu-west-1 = {
              security-group = module.utilities-regional-primary.security-group-id,
              ami            = "ami-0aef57767f5404a3c"
            }
          }
        },
        {
          name                  = "Windows Server 2019",
          connection-protocol   = "rdp",
          instance-profile-name = module.utilities-global.instance-profile-name,
          template-filename     = "cfn-templates/windows_server_2019.yaml",
          user-data-file        = "user-data/windows.ps1",
          region-map = {
            eu-west-1 = {
              security-group = module.utilities-regional-primary.security-group-id,
              ami            = "ami-0a262e3ac12949132"
            }
            us-east-1 = {
              security-group = module.utilities-regional-secondary.security-group-id,
              ami            = "ami-0eb7fbcc77e5e6ec6"

            }
          }
        },
      ],
      max-instance-count  = "5",
      max-days-to-expiry  = "7",
      max-extension-count = "3",
    },
    quail-quants = {
      instance-types = ["t3.micro", "t3.small"],
      operating-systems = [
        {
          name                  = "AWS Linux 2",
          instance-profile-name = module.utilities-global.instance-profile-name,
          connection-protocol   = "ssh",
          template-filename     = "cfn-templates/aws_linux.yaml",
          user-data-file        = "user-data/linux.sh",
          region-map = {
            eu-west-1 = {
              security-group = module.utilities-regional-primary.security-group-id,
              ami            = "ami-0bb3fad3c0286ebd5"
            }
          }
        },
        {
          name                  = "Windows Server 2019",
          instance-profile-name = module.utilities-global.instance-profile-name,
          connection-protocol   = "rdp",
          template-filename     = "cfn-templates/windows_server_2019.yaml",
          user-data-file        = "user-data/windows.ps1",
          region-map = {
            eu-west-1 = {
              security-group = module.utilities-regional-primary.security-group-id,
              ami            = "ami-0a262e3ac12949132"
            }
          }
        },
        {
          name                  = "Ubuntu 20.04",
          instance-profile-name = module.utilities-global.instance-profile-name,
          connection-protocol   = "ssh",
          template-filename     = "cfn-templates/ubuntu_2004.yaml",
          user-data-file        = "user-data/linux.sh",
          region-map = {
            eu-west-1 = {
              security-group = module.utilities-regional-primary.security-group-id,
              ami            = "ami-0aef57767f5404a3c"
            }
          }
        },
      ],
      max-instance-count  = "5",
      max-days-to-expiry  = "3",
      max-extension-count = "3",
    },
  }
}

module "backend" {
  source = "../modules/backend"

  # Project definition vars
  project-name    = var.project-name
  region-primary  = var.region-primary
  account-primary = data.aws_caller_identity.primary.account_id

  # Notification and email vars
  notification-email                = var.notification-email
  admin-email                       = var.admin-email
  cleanup-notice-notification-hours = var.cleanup-notice-notification-hours
  external-sns-failure-topic-arn    = var.external-sns-failure-topic-arn

  # Auth vars
  support-localhost-urls = var.support-localhost-urls
  hosting-domain         = var.hosting-domain
  hosted-zone-name       = var.hosted-zone-name
  jwt-issuer = module.okta-app.auth_server_issuer
  jwt-audience = [module.okta-app.oauth_app_client_id]

  # Tag config
  instance-tags = var.instance-tags
  resource-tags = var.resource-tags

  # DynamoDB configuration data
  regional-data   = local.regional-data
  permission-data = local.permission-data

  # Other
  cfn_data_bucket = aws_s3_bucket.cfn_data_bucket.bucket
}

module "frontend" {
  source = "../modules/frontend"

  # Project definition vars
  project-name    = var.project-name
  region-primary  = var.region-primary
  account-primary = data.aws_caller_identity.primary.account_id

  # Tag config
  resource-tags = var.resource-tags

  # Application config
  api-root-url      = module.backend.api-root-url

  # Okta Auth config
  jwt-issuer = module.okta-app.auth_server_issuer
  jwt-client-id = module.okta-app.oauth_app_client_id
}

module "frontend-ecs-hosting" {
  source = "../modules/frontend-ecs-hosting"

  # Project definition vars
  project-name    = var.project-name
  region-primary  = var.region-primary
  account-primary = data.aws_caller_identity.primary.account_id

  # Tag config
  resource-tags = var.resource-tags

  # Hosting config
  ecr-repository-url = module.frontend.ecr-repository-url
  ecr-container-name = module.frontend.ecr-image-name
  hosting-domain     = var.hosting-domain
  hosted-zone-name   = var.hosted-zone-name
}

module "utilities-global" {
  source = "../modules/utilities-global"

  # Project definition vars
  project-name = var.project-name

  # Tag config
  resource-tags = var.resource-tags
}

module "utilities-regional-primary" {
  source = "../modules/utilities-regional"

  # Project definition vars
  project-name = var.project-name

  # Tag config
  resource-tags = var.resource-tags
}

module "utilities-regional-secondary" {
  source = "../modules/utilities-regional"

  providers = {
    aws = aws.secondary
  }

  # Project definition vars
  project-name = var.project-name

  # Tag config
  resource-tags = var.resource-tags
}

module "okta-app" {
  source = "../modules/okta-app"

  project-name = var.project-name
  okta-groups = module.okta-data.okta-groups
}

module "okta-data" {
  source = "../modules/okta-data"

  project-name = var.project-name
}