resource "random_pet" "lab" {
  length    = 2
  separator = "-"
}

locals {
  lab_id = "${var.env_name}-${var.cloud}-${random_pet.lab.id}"
}
