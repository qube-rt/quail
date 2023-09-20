resource "aws_ecr_repository" "private_api" {
  name                 = local.ecr_private_api_name
  image_tag_mutability = "MUTABLE"
  tags                 = local.resource_tags
}

resource "docker_image" "private_api" {
  name         = local.ecr_private_api_name
  keep_locally = false

  build {
    context    = "${path.module}/quail-api"
    dockerfile = "Dockerfile"
    target     = "production_private_api"
    build_args = {
      INSTALL_PYTHON_VERSION = 3.9
      PIP_INDEX_URL          = var.pip_index_url
      http_proxy             = var.http_proxy
      https_proxy            = var.https_proxy
      no_proxy               = var.no_proxy
    }
    tag = [aws_ecr_repository.private_api.repository_url]
  }

  triggers = {
    # Only rebuild if any of the source files, assets or dependencies have changed.
    dir_sha1 = sha1(
      join("", [for f in tolist(fileset(".", "${path.module}/quail-api/**")) : filesha1(f)])
    )
  }
}

# Build and push the image to the repository
resource "null_resource" "private_api_image_publish" {
  provisioner "local-exec" {
    command = <<-EOT
      aws ecr get-login-password --region ${var.region-primary} | \
        docker login --username AWS --password-stdin ${var.account-primary}.dkr.ecr.${var.region-primary}.amazonaws.com
      docker push ${aws_ecr_repository.private_api.repository_url}
    EOT
  }

  triggers = {
    run_on_change = docker_image.private_api.repo_digest
  }

  # Must be run after the docker image has been built
  depends_on = [docker_image.private_api]
}

data "aws_ecr_image" "private_api" {
  repository_name = local.ecr_private_api_name
  image_tag       = "latest"

  depends_on = [null_resource.private_api_image_publish]
}
