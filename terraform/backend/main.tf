locals {
  name_prefix = "${var.project_name}-${var.environment}"
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

resource "digitalocean_database_cluster" "redis" {
  count      = var.create_redis ? 1 : 0
  name       = "${local.name_prefix}-redis"
  engine     = "redis"
  version    = var.redis_version
  size       = var.redis_size
  region     = var.region
  node_count = var.redis_node_count
}
