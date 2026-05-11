variable "aws_region" {
  type        = string
  description = "AWS region for the TRIDENT control plane."
  default     = "us-east-1"
}

variable "project_name" {
  type        = string
  description = "Name prefix for AWS resources."
  default     = "trident"
}

variable "artifact_bucket_name" {
  type        = string
  description = "Globally unique S3 bucket for reports, molecules, and cached artifacts."
}

variable "subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs for EKS."
}

variable "neo4j_aura_uri" {
  type        = string
  description = "Neo4j Aura connection URI used by the deployed API."
  sensitive   = true
}
