output "okta-groups" {
  description = "The groups generated for the app"
  value = [
    okta_group.admins.id,
    okta_group.developers.id,
    okta_group.quants.id
  ]
}
