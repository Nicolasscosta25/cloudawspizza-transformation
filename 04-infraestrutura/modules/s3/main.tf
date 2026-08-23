resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "static" {
  bucket = "${var.project_name}-static-${random_id.suffix.hex}"

  tags = {
    Name    = "${var.project_name}-static"
    Project = "CloudAWSPizza"
  }
}

resource "aws_s3_bucket_public_access_block" "static" {
  bucket = aws_s3_bucket.static.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "static" {
  bucket = aws_s3_bucket.static.id

  versioning_configuration {
    status = "Enabled"
  }
}
