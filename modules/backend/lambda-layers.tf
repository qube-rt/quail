locals {
  marshmallow_layer_filename = "${path.module}/build/marshmallow-layer.zip"
  jinja_layer_filename       = "${path.module}/build/jinja-layer.zip"
}

# Marshmallow Lambda Layer
resource "null_resource" "marshmallow_layer_install" {
  provisioner "local-exec" {
    working_dir = local.lambda_layer_path
    command     = "pip install --upgrade --target ./marshmallow/python -r marshmallow-requirements.txt"
  }

  triggers = {
    # Rerun only when requirements updated
    rerun_for = base64sha256(file("${local.lambda_layer_path}/marshmallow-requirements.txt"))
  }
}

data "archive_file" "marshmallow_layer_package" {
  type        = "zip"
  source_dir  = "${local.lambda_layer_path}/marshmallow/"
  output_path = local.marshmallow_layer_filename

  depends_on = [null_resource.marshmallow_layer_install]
}

resource "aws_lambda_layer_version" "marshmallow_layer" {
  layer_name          = "${var.project-name}-marshmallow-layer"
  filename            = local.marshmallow_layer_filename
  source_code_hash    = data.archive_file.marshmallow_layer_package.output_base64sha256
  compatible_runtimes = ["python3.8"]

  depends_on = [data.archive_file.marshmallow_layer_package]
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
