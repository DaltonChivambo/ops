#!/bin/sh
# Cria uma base e um role por serviço, e fecha as ligações cruzadas.
#
# «Database per service» não exige um servidor por serviço — exige que nenhum
# serviço consiga chegar à base do outro. É o REVOKE que garante isso: sem ele,
# no dia em que alguém escrever um JOIN entre bases, a regra deixou de existir.
#
# Shell e não .sql porque as senhas vêm do ambiente e não podem ficar no ficheiro.
#
# `sh` e não `bash`: a imagem `postgres:18-alpine` não traz bash, só o `ash` do
# busybox via `/bin/sh`. Sem pipes no script, `set -eu` chega — `pipefail` não
# existe em POSIX sh.
set -eu

create_database() {
  local database="$1" user="$2" password="$3"

  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
	CREATE ROLE "${user}" LOGIN PASSWORD '${password}';
	CREATE DATABASE "${database}" OWNER "${user}";
	-- Por omissão, PUBLIC pode ligar-se a qualquer base. É isso que se revoga.
	REVOKE CONNECT ON DATABASE "${database}" FROM PUBLIC;
	GRANT  CONNECT ON DATABASE "${database}" TO "${user}";
SQL

  # O schema `public` pertence ao pg_database_owner desde o PostgreSQL 15, mas
  # o dono da base não recebe automaticamente CREATE nele. Sem isto, o Alembic
  # falha na primeira migração.
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$database" <<-SQL
	GRANT ALL ON SCHEMA public TO "${user}";
SQL
}

# Base de testes: mesmo dono, para o pytest correr migrações sem privilégios extra.
create_test_database() {
  local database="$1" user="$2"

  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
	CREATE DATABASE "${database}" OWNER "${user}";
	REVOKE CONNECT ON DATABASE "${database}" FROM PUBLIC;
	GRANT  CONNECT ON DATABASE "${database}" TO "${user}";
SQL

  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$database" <<-SQL
	GRANT ALL ON SCHEMA public TO "${user}";
SQL
}

create_database "mozaops_closing_reconciliation" "$DB_RECONCILIATION_USER" "$DB_RECONCILIATION_PASSWORD"
create_database "mozaops_cases"                  "$DB_CASES_USER"          "$DB_CASES_PASSWORD"
create_database "keycloak"                       "$DB_KEYCLOAK_USER"       "$DB_KEYCLOAK_PASSWORD"

create_test_database "mozaops_closing_reconciliation_test" "$DB_RECONCILIATION_USER"
create_test_database "mozaops_cases_test"                  "$DB_CASES_USER"

echo "MozaOps: bases criadas, com as ligações cruzadas fechadas."
