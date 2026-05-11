output "eks_cluster_name" {
  value       = aws_eks_cluster.trident.name
  description = "TRIDENT EKS cluster name."
}

output "artifact_bucket" {
  value       = aws_s3_bucket.artifacts.bucket
  description = "S3 bucket for TRIDENT reports and design artifacts."
}

output "neo4j_aura_uri_configured" {
  value       = var.neo4j_aura_uri != ""
  description = "Whether Neo4j Aura connection configuration was supplied."
  sensitive   = true
}
