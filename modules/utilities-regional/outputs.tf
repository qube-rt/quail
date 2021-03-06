output "vpc-id" {
  description = "ID of the created VPC."
  value       = aws_vpc.main.id
}

output "subnet-ids" {
  description = "IDs of the subnets associated with the VPC."
  value       = aws_subnet.public.*.id
}

output "security-group-id" {
  description = "ID of the security group to be used by instances."
  value       = aws_security_group.instance_sg.id
}

output "ssh-key-name" {
  description = "Name of the SSH key for instances in the region."
  value       = aws_key_pair.ec2_key.key_name
}
