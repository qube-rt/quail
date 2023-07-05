locals {
  resource_tags = merge(
    {
      part_of = var.project-name
    },
    var.resource-tags
  )
}
