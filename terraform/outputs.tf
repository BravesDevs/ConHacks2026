output "postgres_cluster_id" {
  value = digitalocean_database_cluster.postgres.id
}

output "postgres_database_name" {
  value = digitalocean_database_db.postgres_app.name
}

output "postgres_user" {
  value = digitalocean_database_user.postgres_app.name
}

output "postgres_uri" {
  description = "Connection string for Postgres (use as DATABASE_URL)."
  value       = digitalocean_database_cluster.postgres.uri
  sensitive   = true
}

output "postgres_private_uri" {
  description = "Private network connection string for Postgres."
  value       = digitalocean_database_cluster.postgres.private_uri
  sensitive   = true
}

output "redis_cluster_id" {
  value = var.create_redis ? digitalocean_database_cluster.redis[0].id : null
}

output "redis_uri" {
  description = "Connection string for Redis (use as REDIS_URL)."
  value       = var.create_redis ? digitalocean_database_cluster.redis[0].uri : null
  sensitive   = true
}

output "redis_private_uri" {
  description = "Private network connection string for Redis."
  value       = var.create_redis ? digitalocean_database_cluster.redis[0].private_uri : null
  sensitive   = true
}
