output "lab_role_arn" {
  value = data.aws_iam_role.lab_role.arn
}

output "instance_profile_name" {
  value = data.aws_iam_instance_profile.lab_profile.name
}
