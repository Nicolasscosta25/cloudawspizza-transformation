variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "cloudawspizza"
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  type    = string
  default = "10.0.1.0/24"
}

variable "private_subnet_cidrs" {
  type    = list(string)
  default = ["10.0.2.0/24", "10.0.3.0/24"]
}

variable "availability_zones" {
  type    = list(string)
  default = ["us-east-1a", "us-east-1b"]
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "db_instance_class" {
  type    = string
  default = "db.t3.micro"
}

variable "db_name" {
  type    = string
  default = "cloudawspizza"
}

variable "db_username" {
  type    = string
  default = "cloudawspizza_admin"
}

# vockey e a keypair padrao ja provisionada em toda conta AWS Academy Learner Lab.
variable "key_name" {
  type    = string
  default = "vockey"
}

# IP publico do operador, usado para restringir o acesso SSH (porta 22) na SG da EC2.
variable "allowed_ssh_cidr" {
  type = string
}
