output "ecr-image-uri" {
  description = "The URI of ECR image responsible for hosting the client app."
  value       = "${aws_ecr_repository.react_frontend.repository_url}@${data.aws_ecr_image.react_frontend.id}"
}

output "ecr-image-name" {
  description = "The name of the ECR image serving the application's UI."
  value       = local.ecr_image_name
}
