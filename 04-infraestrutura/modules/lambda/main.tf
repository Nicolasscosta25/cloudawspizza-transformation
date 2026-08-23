data "archive_file" "notify_order" {
  type        = "zip"
  source_file = "${path.module}/src/notify_order.py"
  output_path = "${path.module}/build/notify_order.zip"
}

resource "aws_lambda_function" "notify_order" {
  function_name    = "${var.project_name}-notify-order"
  role             = var.lab_role_arn
  handler          = "notify_order.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.notify_order.output_path
  source_code_hash = data.archive_file.notify_order.output_base64sha256
  timeout          = 10

  tags = {
    Project = "CloudAWSPizza"
  }
}
