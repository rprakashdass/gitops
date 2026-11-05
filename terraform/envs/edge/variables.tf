variable "domain" {
  type    = string
  default = "rprakashdass.in"
}

variable "zone_id" {
  type = string
}

variable "vm_public_ip" {
  type = string
}

variable "azure_subscription_id" {
  type = string
}

variable "resource_group_name" {
  type    = string
  default = "reverseProxy"
}

variable "nsg_name" {
  type    = string
  default = "proxy-nsg"
}
