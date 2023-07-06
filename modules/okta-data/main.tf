resource "okta_group" "admins" {
  name        = var.admin-group-name
  description = "${var.project-name} admin users"
}

resource "okta_group" "developers" {
  name        = "${var.project-name}-developers"
  description = "${var.project-name} developer users"
}

resource "okta_group" "quants" {
  name        = "${var.project-name}-quants"
  description = "${var.project-name} quant developers"
}

resource "okta_user" "alice" {
  first_name = "Alice"
  last_name  = "Admin"
  login      = "alice@example.com"
  email      = "alice@example.com"
  password   = "i@m4dmin"
}

resource "okta_user" "bob" {
  first_name = "Bob"
  last_name  = "Dev"
  login      = "bob@example.com"
  email      = "bob@example.com"
  password   = "i@md3veloper"
}

resource "okta_user" "charlie" {
  first_name = "Charlie"
  last_name  = "Quant"
  login      = "charlie@example.com"
  email      = "charlie@example.com"
  password   = "i@mqu4nt"
}

resource "okta_group_memberships" "admins" {
  group_id = okta_group.admins.id
  users = [
    okta_user.alice.id
  ]
}

resource "okta_group_memberships" "developers" {
  group_id = okta_group.developers.id
  users = [
    okta_user.alice.id,
    okta_user.bob.id
  ]
}

resource "okta_group_memberships" "quants" {
  group_id = okta_group.quants.id
  users = [
    okta_user.charlie.id
  ]
}
