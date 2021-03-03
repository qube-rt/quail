resource "aws_ecr_repository" "hosting_repository" {
  name                 = local.ecr_image_name
  image_tag_mutability = "MUTABLE"
  tags                 = local.resource_tags
}

# Build and push the image to the repository
resource "null_resource" "nginx_docker_build" {
  provisioner "local-exec" {
    command = <<-EOT
      docker build -f ${path.module}/nginx/Dockerfile -t ${local.ecr_image_name} ${path.module}
      docker tag ${local.ecr_image_name} ${aws_ecr_repository.hosting_repository.repository_url}
      aws ecr get-login-password --region eu-west-1 | \
        docker login --username AWS --password-stdin ${var.account-primary}.dkr.ecr.${var.region-primary}.amazonaws.com
      docker push ${aws_ecr_repository.hosting_repository.repository_url}
    EOT
  }

  triggers = {
    run_once = fileexists("${local.frontend_path}/build/asset-manifest.json") ? base64sha256(file("${local.frontend_path}/build/asset-manifest.json")) : "build"
    # rerun_every_time = uuid()
  }

  # Must be run after the frontend resources have been built
  depends_on = [null_resource.frontend_build]
}
