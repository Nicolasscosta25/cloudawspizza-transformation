output "ec2_public_ip" {
  value = module.ec2.public_ip
}

output "ec2_public_dns" {
  value = module.ec2.public_dns
}

output "ssh_command" {
  value = "ssh -i vockey.pem ec2-user@${module.ec2.public_ip}"
}

output "rds_endpoint" {
  value = module.rds.db_endpoint
}

output "rds_port" {
  value = module.rds.db_port
}

output "rds_password" {
  value     = module.rds.db_password
  sensitive = true
}

output "s3_bucket_name" {
  value = module.s3.bucket_name
}

output "lambda_function_name" {
  value = module.lambda.function_name
}
