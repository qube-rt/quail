locals {
  cross-account-role-name = "${var.project-name}-cross-account"
  admin-group-name        = "${var.project-name}-admins"

  regional-data = [
    {
      account-id   = "442249827373",
      region       = "eu-west-1",
      ssh-key-name = module.utilities-regional-primary.ssh-key-name,
      vpc-id       = module.utilities-regional-primary.vpc-id,
      subnet-id    = module.utilities-regional-primary.subnet-ids,
    },
    {
      account-id   = "442249827373",
      region       = "us-east-1",
      ssh-key-name = module.utilities-regional-secondary.ssh-key-name,
      vpc-id       = module.utilities-regional-secondary.vpc-id,
      subnet-id    = module.utilities-regional-secondary.subnet-ids,
    },
    {
      account-id   = "815246801749",
      region       = "eu-west-1",
      ssh-key-name = module.utilities-regional-second-account-main-region.ssh-key-name,
      vpc-id       = module.utilities-regional-second-account-main-region.vpc-id,
      subnet-id    = module.utilities-regional-second-account-main-region.subnet-ids,
    },
  ]

  permission-data = {
    quail-developers = {
      instance-types = ["t3.nano", "t3.micro", "t3.small"],
      operating-systems = [
        {
          name                = "AWS Linux 2",
          connection-protocol = "ssh",
          template-filename   = "cfn-templates/aws_linux.yaml",
          user-data-file      = "user-data/linux.sh",
          region-map = {
            "442249827373" = {
              eu-west-1 = {
                security-group        = module.utilities-regional-primary.security-group-id,
                instance-profile-name = module.utilities-account-first.instance-profile-name,
                ami                   = "ami-0bb3fad3c0286ebd5"
              }
              us-east-1 = {
                security-group        = module.utilities-regional-secondary.security-group-id,
                instance-profile-name = module.utilities-account-first.instance-profile-name,
                ami                   = "ami-09te47d2ba12ee1ff75"
              }
            }
            "815246801749" = {
              eu-west-1 = {
                security-group        = module.utilities-regional-second-account-main-region.security-group-id,
                instance-profile-name = module.utilities-account-second.instance-profile-name,
                ami                   = "ami-09f6caae59175ba13"
              }
            }
          }
        },
        {
          name                  = "Ubuntu 20.04",
          connection-protocol   = "ssh",
          instance-profile-name = module.utilities-account-first.instance-profile-name,
          template-filename     = "cfn-templates/ubuntu_2004.yaml",
          user-data-file        = "user-data/linux.sh",
          region-map = {
            "442249827373" = {
              eu-west-1 = {
                security-group        = module.utilities-regional-primary.security-group-id,
                instance-profile-name = module.utilities-account-first.instance-profile-name,
                ami                   = "ami-0aef57767f5404a3c"
              },
            },
            "815246801749" = {
              eu-west-1 = {
                security-group        = module.utilities-regional-second-account-main-region.security-group-id,
                instance-profile-name = module.utilities-account-second.instance-profile-name,
                ami                   = "ami-0136ddddd07f0584f"
              }
            }
          }
        },
        {
          name                  = "Windows Server 2019",
          connection-protocol   = "rdp",
          instance-profile-name = module.utilities-account-first.instance-profile-name,
          template-filename     = "cfn-templates/windows_server_2019.yaml",
          user-data-file        = "user-data/windows.ps1",
          region-map = {
            "442249827373" = {
              eu-west-1 = {
                security-group        = module.utilities-regional-primary.security-group-id,
                instance-profile-name = module.utilities-account-first.instance-profile-name,
                ami                   = "ami-0a262e3ac12949132"
              }
              us-east-1 = {
                security-group        = module.utilities-regional-secondary.security-group-id,
                instance-profile-name = module.utilities-account-first.instance-profile-name,
                ami                   = "ami-0eb7fbcc77e5e6ec6"
              }
            }
            "815246801749" = {
              eu-west-1 = {
                security-group        = module.utilities-regional-second-account-main-region.security-group-id,
                instance-profile-name = module.utilities-account-second.instance-profile-name,
                ami                   = "ami-09a485cf21c2d65e1"
              }
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
      accounts       = ["442249827373", "815246801749"],
      operating-systems = [
        {
          name                  = "AWS Linux 2",
          instance-profile-name = module.utilities-account-first.instance-profile-name,
          connection-protocol   = "ssh",
          template-filename     = "cfn-templates/aws_linux.yaml",
          user-data-file        = "user-data/linux.sh",
          region-map = {
            "442249827373" = {
              eu-west-1 = {
                security-group        = module.utilities-regional-primary.security-group-id,
                instance-profile-name = module.utilities-account-first.instance-profile-name,
                ami                   = "ami-0bb3fad3c0286ebd5"
              }
            }
          }
        },
        {
          name                  = "Windows Server 2019",
          instance-profile-name = module.utilities-account-first.instance-profile-name,
          connection-protocol   = "rdp",
          template-filename     = "cfn-templates/windows_server_2019.yaml",
          user-data-file        = "user-data/windows.ps1",
          region-map = {
            "442249827373" = {
              eu-west-1 = {
                security-group        = module.utilities-regional-primary.security-group-id,
                instance-profile-name = module.utilities-account-first.instance-profile-name,
                ami                   = "ami-0a262e3ac12949132"
              }
            }
          }
        },
        {
          name                  = "Ubuntu 20.04",
          instance-profile-name = module.utilities-account-first.instance-profile-name,
          connection-protocol   = "ssh",
          template-filename     = "cfn-templates/ubuntu_2004.yaml",
          user-data-file        = "user-data/linux.sh",
          region-map = {
            "442249827373" = {
              eu-west-1 = {
                security-group        = module.utilities-regional-primary.security-group-id,
                instance-profile-name = module.utilities-account-first.instance-profile-name,
                ami                   = "ami-0aef57767f5404a3c"
              }
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
  jwt-issuer             = module.okta-app.auth_server_issuer
  jwt-audience           = [module.okta-app.oauth_app_client_id]
  admin-group-name       = local.admin-group-name

  # Tag config
  instance-tags = var.instance-tags
  resource-tags = var.resource-tags

  # DynamoDB configuration data
  regional-data   = local.regional-data
  permission-data = local.permission-data

  # Other
  cfn_data_bucket         = aws_s3_bucket.cfn_data_bucket.bucket
  cross-account-role-name = local.cross-account-role-name
  remote-accounts         = [data.aws_caller_identity.second.account_id]
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
  api-root-url = module.backend.api-root-url

  # Okta Auth config
  jwt-issuer    = module.okta-app.auth_server_issuer
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

############################################
# Infrastructure set up in the first account
############################################
module "utilities-account-first" {
  source = "../modules/utilities-account"

  # Project definition vars
  project-name            = var.project-name
  account-primary         = data.aws_caller_identity.primary.account_id
  user-data-bucket        = aws_s3_bucket.cfn_data_bucket.arn
  cross-account-role-name = local.cross-account-role-name
  cross-account-principals = [
    module.backend.public-api-assumed-role,
    module.backend.private-api-assumed-role,
  ]

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
    aws = aws.secondary-region
  }

  # Project definition vars
  project-name = var.project-name

  # Tag config
  resource-tags = var.resource-tags
}

#############################################
# Infrastructure set up in the second account
#############################################
module "utilities-account-second" {
  source = "../modules/utilities-account"

  providers = {
    aws = aws.secondary-account-main-region
  }

  # Project definition vars
  project-name            = var.project-name
  account-primary         = data.aws_caller_identity.primary.account_id
  user-data-bucket        = aws_s3_bucket.cfn_data_bucket.arn
  cross-account-role-name = local.cross-account-role-name
  cross-account-principals = [
    module.backend.public-api-assumed-role,
    module.backend.private-api-assumed-role,
  ]

  # Tag config
  resource-tags = var.resource-tags
}

module "utilities-regional-second-account-main-region" {
  source = "../modules/utilities-regional"

  providers = {
    aws = aws.secondary-account-main-region
  }

  # Project definition vars
  project-name = var.project-name

  # Tag config
  resource-tags = var.resource-tags
}

###################
# Identity provider
###################
module "okta-app" {
  source = "../modules/okta-app"

  project-name = var.project-name
  okta-groups  = module.okta-data.okta-groups
}

module "okta-data" {
  source = "../modules/okta-data"

  project-name     = var.project-name
  admin-group-name = local.admin-group-name
}