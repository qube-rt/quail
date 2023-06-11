locals {
  frontend_path = "${path.module}/frontend"

  react_config = <<-EOT
  REACT_APP_API_HOST=${var.api-root-url}
  REACT_APP_JWT_ISSUER=${var.jwt-issuer}
  REACT_APP_JWT_CLIENT_ID=${var.jwt-client-id}
  EOT
}

# Generate an .env file to be used by the app
resource "local_file" "react_env" {
  filename = "${local.frontend_path}/.env"
  content  = local.react_config
}

resource "aws_ecr_repository" "hosting_repository" {
  name                 = local.ecr_image_name
  image_tag_mutability = "MUTABLE"
  tags                 = local.resource_tags
}

resource "docker_image" "nginx" {
  name         = local.ecr_image_name
  keep_locally = true

  build {
    context    = path.module
    dockerfile = "nginx/Dockerfile"
    tag        = [aws_ecr_repository.hosting_repository.repository_url]
  }

  triggers = {
    # Only rebuild if any of the source files, assets or dependencies have changed.
    dir_sha1 = sha1(
      join("", [for f in concat(
        tolist(fileset(".", "${path.module}/frontend/src/**")),
        tolist(fileset(".", "${path.module}/frontend/public/**")),
        tolist(fileset(".", "${path.module}/frontend/public/.env")),
        [
          "${path.module}/frontend/package.json",
          "${path.module}/frontend/package-lock.json"
        ]
      ) : filesha1(f)])
    )
  }

  depends_on = [local_file.react_env]
}

# Build and push the image to the repository
resource "null_resource" "nginx_image_publish" {
  provisioner "local-exec" {
    command = <<-EOT
      aws ecr get-login-password --region eu-west-1 | \
        docker login --username AWS --password-stdin ${var.account-primary}.dkr.ecr.${var.region-primary}.amazonaws.com
      docker push ${aws_ecr_repository.hosting_repository.repository_url}
    EOT
  }

  triggers = {
    run_once = docker_image.nginx.repo_digest
  }

  # Must be run after the frontend resources have been built
  depends_on = [docker_image.nginx]
}
