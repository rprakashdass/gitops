resource "cloudflare_dns_record" "wildcard" {
  zone_id = var.zone_id
  name    = "*.${var.domain}"
  type    = "A"
  content = var.vm_public_ip
  ttl     = 300
  proxied = false
}

resource "azurerm_network_security_rule" "web" {
  for_each = {
    http  = { port = 80, priority = 320 }
    https = { port = 443, priority = 310 }
  }

  name                        = "allow-${each.key}"
  priority                    = each.value.priority
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = each.value.port
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = var.nsg_name
}
