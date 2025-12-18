resource "random_pet" "suffix" {
  length    = 2
  separator = "-"
}

locals {
  # Tight-ish naming to avoid Azure resource length limits.
  env_compact = lower(regexreplace(var.env_name, "[^0-9a-zA-Z]", ""))
  prefix      = substr(local.env_compact, 0, 10)
  suffix      = substr(replace(random_pet.suffix.id, "-", ""), 0, 8)

  name_base = "${local.prefix}${local.suffix}"

  rg_name = coalesce(var.resource_group_name, "rg-${local.name_base}")

  vnet_name   = "vnet-${local.name_base}"
  subnet_name = "subnet-web"
  nsg_name    = "nsg-web-${local.name_base}"

  lb_pip_name = "pip-lb-${local.name_base}"
  lb_name     = "lb-web-${local.name_base}"

  vm_names = [
    substr("vm1-${local.name_base}", 0, 15),
    substr("vm2-${local.name_base}", 0, 15),
  ]

  cloud_init = <<-EOT
    #cloud-config
    package_update: true
    packages:
      - nginx
    runcmd:
      - [ bash, -lc, "systemctl enable nginx" ]
      - [ bash, -lc, "systemctl restart nginx" ]
      - [ bash, -lc, "echo '${var.env_name} $(hostname)' > /var/www/html/index.nginx-debian.html" ]
  EOT
}

resource "azurerm_resource_group" "rg" {
  name     = local.rg_name
  location = var.location
}

resource "azurerm_virtual_network" "vnet" {
  name                = local.vnet_name
  address_space       = ["10.10.0.0/16"]
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_subnet" "subnet" {
  name                 = local.subnet_name
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.10.1.0/24"]
}

resource "azurerm_network_security_group" "nsg" {
  name                = local.nsg_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  security_rule {
    name                       = "allow-ssh"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "allow-http"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "subnet_nsg" {
  subnet_id                 = azurerm_subnet.subnet.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}

resource "azurerm_public_ip" "vm_pip" {
  count               = 2
  name                = "pip-${local.vm_names[count.index]}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  allocation_method = "Static"
  sku               = "Standard"
}

resource "azurerm_network_interface" "nic" {
  count               = 2
  name                = "nic-${local.vm_names[count.index]}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  ip_configuration {
    name                          = "ipconfig1"
    subnet_id                     = azurerm_subnet.subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.vm_pip[count.index].id
  }

  depends_on = [azurerm_subnet_network_security_group_association.subnet_nsg]
}

resource "azurerm_availability_set" "aset" {
  name                = "aset-${local.name_base}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  managed = true
}

resource "azurerm_linux_virtual_machine" "vm" {
  count               = 2
  name                = local.vm_names[count.index]
  computer_name       = local.vm_names[count.index]
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  size                = var.vm_size
  admin_username      = var.admin_username

  network_interface_ids = [azurerm_network_interface.nic[count.index].id]

  availability_set_id = azurerm_availability_set.aset.id

  disable_password_authentication = true

  admin_ssh_key {
    username   = var.admin_username
    public_key = var.ssh_public_key
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  custom_data = base64encode(local.cloud_init)
}

resource "azurerm_public_ip" "lb_pip" {
  name                = local.lb_pip_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  allocation_method = "Static"
  sku               = "Standard"
}

resource "azurerm_lb" "lb" {
  name                = local.lb_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "Standard"

  frontend_ip_configuration {
    name                 = "fe-public"
    public_ip_address_id = azurerm_public_ip.lb_pip.id
  }
}

resource "azurerm_lb_backend_address_pool" "bepool" {
  name            = "be-web"
  loadbalancer_id = azurerm_lb.lb.id
}

resource "azurerm_network_interface_backend_address_pool_association" "nic_assoc" {
  count                   = 2
  network_interface_id    = azurerm_network_interface.nic[count.index].id
  ip_configuration_name   = "ipconfig1"
  backend_address_pool_id = azurerm_lb_backend_address_pool.bepool.id
}

resource "azurerm_lb_probe" "http" {
  name            = "probe-http"
  loadbalancer_id = azurerm_lb.lb.id
  protocol        = "Tcp"
  port            = 80
}

resource "azurerm_lb_rule" "http" {
  name                           = "rule-http"
  loadbalancer_id                = azurerm_lb.lb.id
  protocol                       = "Tcp"
  frontend_port                  = 80
  backend_port                   = 80
  frontend_ip_configuration_name = "fe-public"
  backend_address_pool_ids       = [azurerm_lb_backend_address_pool.bepool.id]
  probe_id                       = azurerm_lb_probe.http.id
}

resource "azurerm_dns_zone" "zone" {
  count               = var.create_dns_zone ? 1 : 0
  name                = var.dns_zone_name
  resource_group_name = azurerm_resource_group.rg.name
}

locals {
  dns_zone_rg   = azurerm_resource_group.rg.name
  dns_zone_name = var.dns_zone_name
  dns_zone_id   = var.create_dns_zone ? azurerm_dns_zone.zone[0].id : null
}

resource "azurerm_dns_a_record" "root" {
  name                = "@"
  zone_name           = local.dns_zone_name
  resource_group_name = local.dns_zone_rg
  ttl                 = 60
  records             = [azurerm_public_ip.lb_pip.ip_address]

  depends_on = [azurerm_dns_zone.zone]
}

resource "azurerm_dns_a_record" "vm" {
  count               = 2
  name                = "vm${count.index + 1}"
  zone_name           = local.dns_zone_name
  resource_group_name = local.dns_zone_rg
  ttl                 = 60
  records             = [azurerm_public_ip.vm_pip[count.index].ip_address]

  depends_on = [azurerm_dns_zone.zone]
}
