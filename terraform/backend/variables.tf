variable "do_token" {
  description = "DigitalOcean API token"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "DigitalOcean region slug"
  type        = string
  default     = "nyc3"
}

variable "environment" {
  description = "Environment name used in resource names (e.g. dev/staging/prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project/app name used in resource names"
  type        = string
  default     = "conhacks"
}

variable "postgres_size" {
  description = "Postgres node size"
  type        = string
  default     = "db-s-1vcpu-1gb"
}

variable "postgres_version" {
  description = "Postgres major version"
  type        = string
  default     = "16"
}

variable "postgres_node_count" {
  description = "Number of nodes in the Postgres cluster"
  type        = number
  default     = 1
}

variable "postgres_db_name" {
  description = "Default application database name"
  type        = string
  default     = "app"
}

variable "create_redis" {
  description = "Whether to provision a managed Redis cluster"
  type        = bool
  default     = true
}

variable "redis_size" {
  description = "Redis node size"
  type        = string
  default     = "db-s-1vcpu-1gb"
}

variable "redis_version" {
  description = "Redis major version"
  type        = string
  default     = "7"
}

variable "redis_node_count" {
  description = "Number of nodes in the Redis cluster"
  type        = number
  default     = 1
}
