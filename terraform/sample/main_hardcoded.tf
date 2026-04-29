locals {
  name_prefix = "conhacks-dev"
}

resource "digitalocean_ssh_key" "default" {
  name       = "${local.name_prefix}-key"
  public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMockKeyForDemoOnly conhacks@demo"
}

resource "digitalocean_droplet" "app" {
  name   = "${local.name_prefix}-droplet"
  region = "nyc3"
  size   = "s-4vcpu-8gb"
  image  = "ubuntu-22-04-x64"

  ssh_keys = [digitalocean_ssh_key.default.fingerprint]
}
