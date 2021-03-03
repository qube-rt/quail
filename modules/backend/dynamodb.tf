## Table storing cross-region and cross-account configuration data
resource "aws_dynamodb_table" "dynamodb-regional-metadata-table" {
  name         = "${var.project-name}-regional-data"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "region"
  tags         = local.resource_tags

  attribute {
    name = "region"
    type = "S"
  }
}

resource "aws_dynamodb_table_item" "dynamodb-regional-metadata-items" {
  table_name = aws_dynamodb_table.dynamodb-regional-metadata-table.name
  hash_key   = aws_dynamodb_table.dynamodb-regional-metadata-table.hash_key

  for_each = var.regional-data

  item = jsonencode({
    region     = { "S" = each.key },
    sshKeyName = { "S" = each.value.ssh-key-name },
    vpcId      = { "S" = each.value.vpc-id },
    subnetId   = { "SS" = sort(each.value.subnet-id) },
  })
}

## Table storing current state of instances
resource "aws_dynamodb_table" "dynamodb-state-table" {
  name         = "${var.project-name}-state-data"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "stacksetID"
  tags         = local.resource_tags

  attribute {
    name = "stacksetID"
    type = "S"
  }
}

## Table storing group permissions
resource "aws_dynamodb_table" "permissions-table" {
  name         = "${var.project-name}-permissions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "group"
  tags         = local.resource_tags

  attribute {
    name = "group"
    type = "S"
  }
}

resource "aws_dynamodb_table_item" "permissions-table-items" {
  table_name = aws_dynamodb_table.permissions-table.name
  hash_key   = aws_dynamodb_table.permissions-table.hash_key

  for_each = var.permission-data

  item = jsonencode({
    group = { "S" = each.key },
    # Sorting the list elements to ensure stable ordering.
    # Without it, every apply tried to udpate the ordering of elements.
    instanceTypes     = { "SS" = sort(each.value.instance-types) },
    operatingSystems  = { "S" = jsonencode(each.value.operating-systems) },
    maxInstanceCount  = { "N" = tostring(each.value.max-instance-count) },
    maxExtensionCount = { "N" = tostring(each.value.max-extension-count) },
    maxDaysToExpiry   = { "N" = tostring(each.value.max-days-to-expiry) },
  })
}
