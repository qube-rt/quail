locals {
  resource_tags = merge(
    {
      part_of = var.project-name
    },
    var.resource-tags
  )
  ecr_public_api_name  = "${var.project-name}-public-api"
  ecr_private_api_name = "${var.project-name}-private-api"
}

