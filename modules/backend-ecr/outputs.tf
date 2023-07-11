output "public-api-image-uri" {
  value = "${aws_ecr_repository.public_api.repository_url}@${data.aws_ecr_image.public_api.id}"
}

output "private-api-image-uri" {
  value = "${aws_ecr_repository.private_api.repository_url}@${data.aws_ecr_image.private_api.id}"
}
