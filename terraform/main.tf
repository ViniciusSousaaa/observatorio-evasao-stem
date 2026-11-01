locals {
  labels = {
    projeto        = "observatorio-evasao-stem"
    ambiente       = var.environment
    gerenciado_por = "terraform"
  }
}

resource "random_id" "suffix" {
  byte_length = 3
}

resource "google_project_service" "sqladmin" {
  project            = var.project_id
  service            = "sqladmin.googleapis.com"
  disable_on_destroy = false
}

resource "google_sql_database_instance" "postgres" {
  name                = "${var.instance_name}-${var.environment}-${random_id.suffix.hex}"
  project             = var.project_id
  region              = var.region
  database_version    = var.database_version
  deletion_protection = var.deletion_protection

  settings {
    tier                  = var.tier
    edition               = "ENTERPRISE"
    availability_type     = "ZONAL"
    disk_type             = "PD_SSD"
    disk_size             = var.disk_size_gb
    disk_autoresize       = true
    disk_autoresize_limit = 20

    user_labels = local.labels

    backup_configuration {
      enabled                        = true
      start_time                     = "05:00"
      point_in_time_recovery_enabled = false
      backup_retention_settings {
        retained_backups = 3
      }
    }

    ip_configuration {
      ipv4_enabled = true
      ssl_mode     = "ENCRYPTED_ONLY"

      dynamic "authorized_networks" {
        for_each = var.authorized_networks
        content {
          name  = authorized_networks.value.name
          value = authorized_networks.value.value
        }
      }
    }

    maintenance_window {
      day          = 7
      hour         = 6
      update_track = "stable"
    }

    database_flags {
      name  = "log_connections"
      value = "on"
    }
    database_flags {
      name  = "log_disconnections"
      value = "on"
    }
  }

  depends_on = [google_project_service.sqladmin]
}

resource "google_sql_database" "dw" {
  name      = var.db_name
  project   = var.project_id
  instance  = google_sql_database_instance.postgres.name
  charset   = "UTF8"
  collation = "en_US.UTF8"
}

resource "google_sql_user" "etl" {
  name     = var.db_user
  project  = var.project_id
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
}