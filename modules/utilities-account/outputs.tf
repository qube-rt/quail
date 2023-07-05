output "instance-profile-name" {
  description = "The name of the instance profile to be used by provisioned instances."
  value       = aws_iam_instance_profile.application_profile.name
}

output "instance-profile-role-arn" {
  description = "The arn of the instance profile to be used by provisioned instances."
  value       = aws_iam_role.instance_profile_role.arn
}
