variable "project_id" {
  description = "ID do projeto no Google Cloud."
  type        = string
}

variable "region" {
  description = "Região do Cloud SQL."
  type        = string
  default     = "southamerica-east1"
}

variable "environment" {
  description = "Ambiente de implantação (dev, hml, prod)."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "hml", "prod"], var.environment)
    error_message = "environment deve ser dev, hml ou prod."
  }
}

variable "instance_name" {
  description = "Prefixo do nome da instância Cloud SQL."
  type        = string
  default     = "observatorio-stem-pg"
}

variable "database_version" {
  description = "Versão do PostgreSQL."
  type        = string
  default     = "POSTGRES_16"
}

variable "tier" {
  description = "Tipo de máquina da instância."
  type        = string
  default     = "db-f1-micro"
}

variable "disk_size_gb" {
  description = "Tamanho inicial do disco em GB."
  type        = number
  default     = 10
}

variable "deletion_protection" {
  description = "Proteção contra exclusão acidental."
  type        = bool
  default     = true
}

variable "authorized_networks" {
  description = "Redes (CIDR) autorizadas a conectar via IP público."
  type = list(object({
    name  = string
    value = string
  }))
  default = []

  validation {
    condition     = alltrue([for n in var.authorized_networks : n.value != "0.0.0.0/0"])
    error_message = "Por segurança, 0.0.0.0/0 não é permitido."
  }
}

variable "db_name" {
  description = "Nome do banco de dados."
  type        = string
  default     = "observatorio_stem"
}

variable "db_user" {
  description = "Nome do usuário de banco de dados."
  type        = string
  default     = "etl_user"
}

variable "db_password" {
  description = "Senha do usuário do banco de dados."
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.db_password) >= 12
    error_message = "A senha deve ter no mínimo 12 caracteres."
  }
}