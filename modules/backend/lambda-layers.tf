locals {
  jinja_layer_filename       = "${path.module}/build/jinja-layer.zip"
}

# Jinja Lambda Layer
resource "null_resource" "jinja_layer_install" {
  provisioner "local-exec" {
    working_dir = local.lambda_layer_path
    command     = "pip install --upgrade --target ./jinja/python -r jinja-requirements.txt"
  }

  triggers = {
    # Rerun only when requirements updated
    rerun_for = base64sha256(file("${local.lambda_layer_path}/jinja-requirements.txt"))
  }
}

data "archive_file" "jinja_layer_package" {
  type        = "zip"
  source_dir  = "${local.lambda_layer_path}/jinja/"
  output_path = local.jinja_layer_filename

  depends_on = [null_resource.jinja_layer_install]
}

resource "aws_lambda_layer_version" "jinja_layer" {
  layer_name          = "${var.project-name}-jinja-layer"
  filename            = local.jinja_layer_filename
  source_code_hash    = data.archive_file.jinja_layer_package.output_base64sha256
  compatible_runtimes = ["python3.8"]

  depends_on = [data.archive_file.jinja_layer_package]
}
