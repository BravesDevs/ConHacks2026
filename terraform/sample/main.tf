locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

resource "digitalocean_ssh_key" "default" {
  name       = "${local.name_prefix}-key"
  public_key = var.ssh_public_key
}

resource "digitalocean_droplet" "app" {
  name   = "${local.name_prefix}-droplet"
  region = var.region
  size   = var.droplet_size
  image  = var.droplet_image

  ssh_keys = [digitalocean_ssh_key.default.fingerprint]
}

resource "digitalocean_database_cluster" "postgres" {
  name       = "${local.name_prefix}-postgres"
  engine     = "pg"
  version    = var.postgres_version
  size       = var.postgres_size
  region     = var.region
  node_count = var.postgres_node_count
}

resource "digitalocean_database_db" "postgres_app" {
  cluster_id = digitalocean_database_cluster.postgres.id
  name       = var.postgres_db_name
}

resource "digitalocean_database_user" "postgres_app" {
  cluster_id = digitalocean_database_cluster.postgres.id
  name       = "app"
}
