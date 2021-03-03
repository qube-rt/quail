resource "tls_private_key" "generated_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "ec2_key" {
  key_name   = "${var.project-name}-key"
  public_key = tls_private_key.generated_key.public_key_openssh
}
