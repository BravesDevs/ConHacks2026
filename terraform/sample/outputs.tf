output "droplet_id" {
  value = digitalocean_droplet.app.id
}

output "droplet_ipv4_address" {
  value = digitalocean_droplet.app.ipv4_address
}

output "postgres_cluster_id" {
  value = digitalocean_database_cluster.postgres.id
}

output "postgres_private_uri" {
  value     = digitalocean_database_cluster.postgres.private_uri
  sensitive = true
}

output "postgres_public_uri" {
  value     = digitalocean_database_cluster.postgres.uri
  sensitive = true
}
