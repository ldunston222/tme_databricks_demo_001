variable "env_name" {
  type        = string
  description = "Logical environment name (e.g. demo1)"
}

variable "cloud" {
  type        = string
  description = "Target cloud (e.g. aws|azure|gcp)"
}
