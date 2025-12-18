output "resource_group_name" {
  value = azurerm_resource_group.rg.name
}

output "location" {
  value = azurerm_resource_group.rg.location
}

output "lb_public_ip" {
  value = azurerm_public_ip.lb_pip.ip_address
}

output "vm_public_ips" {
  value = {
    vm1 = azurerm_public_ip.vm_pip[0].ip_address
    vm2 = azurerm_public_ip.vm_pip[1].ip_address
  }
}

output "dns_zone_name" {
  value = var.dns_zone_name
}

output "dns_records" {
  value = {
    root = "${var.dns_zone_name} -> ${azurerm_public_ip.lb_pip.ip_address}"
    vm1  = "vm1.${var.dns_zone_name} -> ${azurerm_public_ip.vm_pip[0].ip_address}"
    vm2  = "vm2.${var.dns_zone_name} -> ${azurerm_public_ip.vm_pip[1].ip_address}"
  }
}
