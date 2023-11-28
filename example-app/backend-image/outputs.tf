output "public-api-image-uri" {
  description = "ECR URI of the public API docker image."
  value       = module.backend-image.public-api-image-uri
}

output "private-api-image-uri" {
  description = "ECR URI of the private API docker image."
  value       = module.backend-image.private-api-image-uri
}
