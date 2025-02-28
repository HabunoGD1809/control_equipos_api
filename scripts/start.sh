#!/bin/bash
set -e

# Esperar a que PostgreSQL esté disponible
if [ -n "$POSTGRES_SERVER" ]; then
  echo "Esperando a que PostgreSQL esté disponible en $POSTGRES_SERVER:$POSTGRES_PORT..."
  while ! nc -z $POSTGRES_SERVER $POSTGRES_PORT; do
    sleep 0.1
  done
  echo "PostgreSQL está disponible"
fi

# Ejecutar migraciones (si se proporciona la variable APPLY_MIGRATIONS)
if [ "$APPLY_MIGRATIONS" = "true" ]; then
  echo "Aplicando migraciones de Alembic..."
  alembic upgrade head
  echo "Migraciones aplicadas"
fi

# Iniciar la aplicación con uvicorn
echo "Iniciando la aplicación..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'
