output "instance_name" {
  description = "Nome da instância Cloud SQL."
  value       = google_sql_database_instance.postgres.name
}

output "instance_connection_name" {
  description = "Connection name para uso com o Cloud SQL Auth Proxy."
  value       = google_sql_database_instance.postgres.connection_name
}

output "public_ip_address" {
  description = "Endereço IP público da instância."
  value       = google_sql_database_instance.postgres.public_ip_address
}

output "database_name" {
  description = "Nome do banco de dados."
  value       = google_sql_database.dw.name
}

output "database_user" {
  description = "Nome do usuário de banco de dados."
  value       = google_sql_user.etl.name
}

output "proxy_command" {
  description = "Comando para inicializar o Cloud SQL Auth Proxy."
  value       = "cloud-sql-proxy --port 5433 ${google_sql_database_instance.postgres.connection_name}"
}