output "frontend-ecr-image-uri" {
  description = "The url of the image in ECR."
  value       = module.frontend-image.ecr-image-uri
}

output "frontend-ecr-image-name" {
  description = "The name of the ECR image serving the application's UI."
  value       = module.frontend-image.ecr-image-name
}
