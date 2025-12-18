variable "env_name" {
  type        = string
  description = "Logical environment name (e.g. demo1)"
}

variable "location" {
  type        = string
  description = "Azure region (e.g. eastus)"
  default     = "eastus"
}

variable "resource_group_name" {
  type        = string
  description = "Resource group name. If null, a name is derived from env_name."
  default     = null
}

variable "admin_username" {
  type        = string
  description = "Admin username for the Linux VMs"
  default     = "azureuser"
}

variable "ssh_public_key" {
  type        = string
  description = "SSH public key (OpenSSH format) for admin_username"
}

variable "vm_size" {
  type        = string
  description = "Azure VM size"
  default     = "Standard_B1s"
}

variable "dns_zone_name" {
  type        = string
  description = "DNS zone name to create/use (e.g. joespizza.com). Public resolution requires registrar delegation to Azure DNS name servers."
  default     = "joespizza.com"
}

variable "create_dns_zone" {
  type        = bool
  description = "Whether to create an Azure DNS zone in the module resource group"
  default     = true
}
