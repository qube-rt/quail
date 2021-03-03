output "ecr-repository-url" {
  description = "The url of the image in ECR."
  value       = aws_ecr_repository.hosting_repository.repository_url
}

output "ecr-image-name" {
  description = "The name of the ECR image serving the application's UI."
  value       = local.ecr_image_name
}
