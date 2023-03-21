# VPC with a public subnet and a security group exposing port 80 for the ECS cluster
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  tags = merge(
    { "Name" : "${var.project-name}-VPC" },
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
  tags = merge(
    { "Name" : "${var.project-name}-Public-Subnet-${count.index}" },
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
    { "Name" : "${var.project-name}-Public-Route-Table" },
    local.resource_tags
  )
}

resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "nginx_sg" {
  vpc_id = aws_vpc.main.id

  ingress {
    cidr_blocks = [
      "0.0.0.0/0",
    ]
    from_port = 80
    protocol  = "tcp"
    to_port   = 80
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    { "Name" : "${var.project-name}-SG" },
    local.resource_tags
  )
}

# CloudWatch log group for the nginx service
resource "aws_cloudwatch_log_group" "ecs_task" {
  name              = "/aws/ecs/${var.ecr-container-name}"
  retention_in_days = 14
  tags              = local.resource_tags
}

# IAM role for the cloudwatch service
resource "aws_iam_role" "ecs_service_role" {
  name               = "${var.project-name}-ecs-nginx-service-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume_role.json
  tags               = local.resource_tags
}

resource "aws_iam_policy_attachment" "ecs_task_execution_policy" {
  name       = "${var.project-name}-ecs-task_execution-policy"
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
  roles      = [aws_iam_role.ecs_service_role.id]
}

# ECS cluster, task definition and service running nginx
resource "aws_ecs_cluster" "main" {
  name               = "${var.project-name}-Cluster"

  tags = local.resource_tags
}

resource "aws_ecs_cluster_capacity_providers" "main_capacity_provider" {
  cluster_name = aws_ecs_cluster.main.name

  capacity_providers = ["FARGATE"]
}

resource "aws_ecs_task_definition" "nginx" {
  family                   = "${var.project-name}-nginx"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  memory                   = "512"
  cpu                      = "256"
  execution_role_arn       = aws_iam_role.ecs_service_role.arn

  container_definitions = jsonencode([
    {
      "name" : "${var.project-name}-nginx",
      "image" : var.ecr-repository-url,
      "essential" : true,
      "portMappings" : [
        {
          "containerPort" : 80,
          "hostPort" : 80
          "protocol" : "tcp"
        }
      ],
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs_task.name
          awslogs-region        = "eu-west-1"
          awslogs-stream-prefix = "ecs"
        }
      }
  }])

  tags = local.resource_tags
}

resource "aws_ecs_service" "nginx" {
  name            = "${var.project-name}-nginx-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.nginx.arn
  launch_type     = "FARGATE"
  desired_count   = length(aws_subnet.public)

  network_configuration {
    assign_public_ip = true
    security_groups  = [aws_security_group.nginx_sg.id]
    subnets          = aws_subnet.public.*.id
  }

  load_balancer {
    container_name   = var.ecr-container-name
    container_port   = 80
    target_group_arn = aws_lb_target_group.ecs_nginx.arn
  }

  tags = local.resource_tags
}

# ELB Service role
resource "aws_iam_role" "ecs_elb_service_role" {
  name               = "ecsServiceRole"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
  tags               = local.resource_tags
}

resource "aws_iam_policy_attachment" "ecs_elb_policy" {
  name       = "${var.project-name}-ecs-elb-policy"
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceRole"
  roles      = [aws_iam_role.ecs_service_role.id]
}

# Application LB 
resource "aws_security_group" "lb_sg" {
  vpc_id = aws_vpc.main.id

  ingress {
    cidr_blocks = [
      "0.0.0.0/0",
    ]
    ipv6_cidr_blocks = [
      "::/0"
    ]
    from_port = 443
    protocol  = "tcp"
    to_port   = 443
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    { "Name" : "${var.project-name}-load-balancer-SG" },
    local.resource_tags
  )
}

resource "aws_lb_target_group" "ecs_nginx" {
  name        = "${var.project-name}-nginx-target-group"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"
  port        = 80
  protocol    = "HTTP"

  tags = local.resource_tags
}

resource "aws_lb" "main" {
  name               = "${var.project-name}-nginx-lb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.lb_sg.id]
  subnets            = aws_subnet.public.*.id

  tags = local.resource_tags
}

data "aws_acm_certificate" "frontend" {
  domain = var.hosting-domain
}

resource "aws_lb_listener" "ecs_nginx_https" {
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = data.aws_acm_certificate.frontend.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ecs_nginx.arn
  }
}

# Route53 config
data "aws_route53_zone" "frontend" {
  name = var.hosted-zone-name
}

resource "aws_route53_record" "frontend" {
  zone_id = data.aws_route53_zone.frontend.zone_id
  name    = var.hosting-domain
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}
