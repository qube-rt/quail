locals {
  frontend_path       = "${path.module}/frontend"
  frontend_build_path = "${path.module}/frontend/build"
  s3_origin_id        = "${var.project-name}-s3-origin"

  react_config = <<-EOT
  REACT_APP_LOGOUT_URL=${var.logout-url}

  REACT_APP_API_HOST=${var.api-root-url}
  REACT_APP_COGNITO_HOST=https://${var.cognito-domain}.auth.${var.region-primary}.amazoncognito.com
  REACT_APP_COGNITO_CLIENT_ID=${var.cognito-client-id}
  EOT
}

# Generate an .env file to be used by the app
resource "local_file" "react_env" {
  filename = "${local.frontend_path}/.env"
  content  = local.react_config
}

# Frontend build and minification
resource "null_resource" "frontend_build" {
  provisioner "local-exec" {
    working_dir = local.frontend_path
    command     = "npm run build"
  }

  triggers = {
    run_once = fileexists("${local.frontend_path}/build/asset-manifest.json") ? base64sha256(file("${local.frontend_path}/build/asset-manifest.json")) : "build"
    # rerun_every_time = uuid()
  }

  depends_on = [local_file.react_env]
}
