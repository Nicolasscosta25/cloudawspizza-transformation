terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "iam" {
  source = "./modules/iam"
}

module "vpc" {
  source = "./modules/vpc"

  project_name         = var.project_name
  vpc_cidr             = var.vpc_cidr
  public_subnet_cidr   = var.public_subnet_cidr
  private_subnet_cidrs = var.private_subnet_cidrs
  availability_zones   = var.availability_zones
}

module "ec2" {
  source = "./modules/ec2"

  project_name           = var.project_name
  vpc_id                 = module.vpc.vpc_id
  public_subnet_id       = module.vpc.public_subnet_id
  instance_type          = var.instance_type
  key_name               = var.key_name
  instance_profile_name  = module.iam.instance_profile_name
  allowed_ssh_cidr       = var.allowed_ssh_cidr
}

module "rds" {
  source = "./modules/rds"

  project_name           = var.project_name
  vpc_id                 = module.vpc.vpc_id
  private_subnet_ids     = module.vpc.private_subnet_ids
  db_instance_class      = var.db_instance_class
  db_name                = var.db_name
  db_username             = var.db_username
  app_security_group_id  = module.ec2.security_group_id
}

module "s3" {
  source = "./modules/s3"

  project_name = var.project_name
}

module "cloudwatch" {
  source = "./modules/cloudwatch"

  project_name = var.project_name
  instance_id  = module.ec2.instance_id
}

module "lambda" {
  source = "./modules/lambda"

  project_name = var.project_name
  lab_role_arn = module.iam.lab_role_arn
}
