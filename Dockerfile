FROM python:3.11-slim

WORKDIR /app

# Establecer variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
   PYTHONUNBUFFERED=1 \
   PYTHONIOENCODING=UTF-8 \
   LANG=C.UTF-8 \
   DEBIAN_FRONTEND=noninteractive \
   TZ=UTC

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
   build-essential \
   libpq-dev \
   tzdata \
   netcat-traditional \
   && apt-get clean \
   && rm -rf /var/lib/apt/lists/*

# Copiar requirements.txt primero para aprovechar la caché de Docker
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && \
   pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Script para esperar a que la base de datos esté disponible antes de iniciar la aplicación
COPY ./scripts/start.sh /start.sh
RUN chmod +x /start.sh

# Exponer puerto
EXPOSE 8000

# Comando para iniciar la aplicación
CMD ["/start.sh"]
