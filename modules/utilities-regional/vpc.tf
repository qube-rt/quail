# VPC with a public subnet and a security group exposing ports 22 (ssh) and 3389 (rdp) from anywhere
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  tags = merge(
    { "Name" : "${var.project-name}-instance-VPC" },
    local.resource_tags
  )
}

resource "aws_internet_gateway" "main_igw" {
  vpc_id = aws_vpc.main.id
  tags = merge(
    { "Name" : "${var.project-name}-IGW" },
    local.resource_tags
  )
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_subnet" "public" {
  count = 2

  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  map_public_ip_on_launch = true
  tags = merge(
    { "Name" : "${var.project-name}-instance-Public-Subnet-${count.index}" },
    local.resource_tags
  )
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main_igw.id
  }

  tags = merge(
    { "Name" : "${var.project-name}-instance-Public-Route-Table" },
    local.resource_tags
  )
}

resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "instance_sg" {
  vpc_id = aws_vpc.main.id

  ingress {
    cidr_blocks = [
      "0.0.0.0/0",
    ]
    from_port = 22
    protocol  = "tcp"
    to_port   = 22
  }

  ingress {
    cidr_blocks = [
      "0.0.0.0/0",
    ]
    from_port = 3389
    protocol  = "tcp"
    to_port   = 3389
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    { "Name" : "${var.project-name}-instance-SG" },
    local.resource_tags
  )
}