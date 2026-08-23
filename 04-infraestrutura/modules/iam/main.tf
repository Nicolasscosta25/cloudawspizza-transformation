# No AWS Academy Learner Lab, a criação de roles/policies IAM é bloqueada pelo
# guardrail da conta. Reaproveitamos a LabRole/LabInstanceProfile já provisionadas
# pela AWS Academy em vez de criar roles com escopo mínimo (o que seria o padrão
# recomendado em uma conta de produção real).

data "aws_iam_role" "lab_role" {
  name = "LabRole"
}

data "aws_iam_instance_profile" "lab_profile" {
  name = "LabInstanceProfile"
}
