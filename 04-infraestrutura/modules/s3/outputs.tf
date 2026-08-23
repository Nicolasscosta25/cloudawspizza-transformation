output "bucket_name" {
  value = aws_s3_bucket.static.bucket
}

output "bucket_arn" {
  value = aws_s3_bucket.static.arn
}
