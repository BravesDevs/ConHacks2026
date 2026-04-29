variable "do_token" {
  description = "DigitalOcean API token"
  type        = string
  sensitive   = true
}

variable "project_name" {
  description = "Project/app name used in resource names"
  type        = string
  default     = "conhacks"
}

variable "environment" {
  description = "Environment name used in resource names (e.g. dev/staging/prod)"
  type        = string
  default     = "dev"
}

variable "region" {
  description = "DigitalOcean region slug"
  type        = string
  default     = "nyc3"
}

variable "ssh_public_key" {
  description = "SSH public key to add to the droplet (contents of your id_ed25519.pub)"
  type        = string
}

variable "droplet_size" {
  description = "Droplet size slug"
  type        = string
  default     = "s-1vcpu-1gb"
}

variable "droplet_image" {
  description = "Droplet image slug"
  type        = string
  default     = "ubuntu-24-04-x64"
}

variable "postgres_size" {
  description = "Postgres node size slug"
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
