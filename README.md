# Sistema de Control de Equipos

API REST moderna para gestionar equipos, movimientos, mantenimiento y documentación asociada, implementada con FastAPI y PostgreSQL.

## Características

- ✅ **Autenticación y Autorización**
  - Sistema JWT para autenticación segura
  - Roles y permisos granulares
  - Registro de actividad y auditoría

- ✅ **Gestión de Equipos**
  - Inventario completo con seguimiento detallado
  - Búsqueda avanzada con texto completo
  - Gestión de estados y proveedores

- ✅ **Control de Movimientos**
  - Registro de salidas y entradas
  - Flujo de autorización configurable
  - Alertas de vencimiento

- ✅ **Sistema de Mantenimiento**
  - Programación de mantenimientos preventivos y correctivos
  - Recordatorios automáticos
  - Historial completo por equipo

- ✅ **Documentación y Reportes**
  - Almacenamiento de documentos por equipo
  - Generación de reportes personalizados
  - Verificación de documentos

## Requisitos previos

- Python 3.10+
- PostgreSQL 14+
- Docker y Docker Compose (opcional, para despliegue containerizado)

## Instalación y ejecución

### Configuración del entorno

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/HabunoGD1809/control-equipos.git
   cd control-equipos
   ```

2. Crear y activar un entorno virtual:
   ```bash
   python -m venv venv
   # En Windows
   venv\Scripts\activate
   # En macOS/Linux
   source venv/bin/activate
   ```

3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Crear el archivo `.env` basado en `.env.example`:
   ```bash
   cp .env.example .env
   ```

### Configuración de la base de datos

1. Crear la base de datos en PostgreSQL:
   ```sql
   CREATE DATABASE control_equipos_db;
   ```

2. Ejecutar las migraciones de Alembic:
   ```bash
   alembic upgrade head
   ```

### Ejecución local

1. Iniciar la API:
   ```bash
   python -m app.main
   ```

2. Acceder a la documentación de la API:
   - Swagger UI: http://localhost:8000/api/v1/docs
   - ReDoc: http://localhost:8000/api/v1/redoc

### Ejecución con Docker

1. Construir y ejecutar los contenedores:
   ```bash
   docker-compose up -d
   ```

2. Acceder a la documentación de la API:
   - Swagger UI: http://localhost:8000/api/v1/docs
   - ReDoc: http://localhost:8000/api/v1/redoc
   - PgAdmin: http://localhost:5050 (email: admin@admin.com, contraseña: admin)

## Estructura del proyecto

El proyecto sigue una arquitectura modular con separación clara de responsabilidades:

- `alembic/`: Configuración y scripts de migración de base de datos
- `app/`: Código fuente principal
  - `api/`: Endpoints y rutas HTTP
  - `core/`: Componentes centrales (seguridad, manejo de errores, etc.)
  - `db/`: Modelos de datos y configuración de base de datos
  - `schemas/`: Esquemas Pydantic para validación y serialización
  - `services/`: Lógica de negocio
  - `tasks/`: Tareas en segundo plano
- `tests/`: Pruebas automatizadas

Para más detalles, consulta [ESTRUCTURA.md](ESTRUCTURA.md).

## Pruebas

Ejecutar las pruebas automatizadas:

```bash
# Todas las pruebas
pytest

# Solo pruebas de una funcionalidad específica
pytest tests/api/test_equipos.py

# Con cobertura
pytest --cov=app
```

## Worker para tareas en segundo plano

El sistema incluye un worker para procesar tareas asíncronas como notificaciones y generación de reportes:

```bash
# Iniciar el worker manualmente
python -m app.worker
```

Este worker se inicia automáticamente con la aplicación, pero puede ejecutarse de forma independiente.

## Migraciones de base de datos

El proyecto utiliza Alembic para gestionar migraciones de base de datos:

```bash
# Crear una nueva migración
alembic revision --autogenerate -m "descripción del cambio"

# Aplicar migraciones pendientes
alembic upgrade head

# Ver historial de migraciones
alembic history --verbose
```

## Guía inicial para uso

1. **Acceso inicial**:
   - Usuario: `admin`
   - Contraseña: `admin_password`

2. **Crear usuarios y roles**:
   - Utiliza los endpoints de `/api/v1/usuarios/` para crear usuarios adicionales
   - Asigna roles apropiados según la función de cada usuario

3. **Configurar catálogos básicos**:
   - Estados de equipo
   - Proveedores
   - Tipos de mantenimiento
   - Tipos de documento

4. **Comenzar a registrar equipos**:
   - Usa el endpoint `/api/v1/equipos/` para dar de alta equipos
   - Adjunta documentación usando `/api/v1/equipos/{equipo_id}/documentos/`

5. **Registrar movimientos**:
   - Utiliza `/api/v1/movimientos/` para registrar salidas y entradas
   - Los movimientos pueden requerir autorización según la configuración

6. **Programar mantenimientos**:
   - Crea programaciones usando `/api/v1/mantenimiento/`
   - Actualiza el estado a medida que avanzan

## Contribución

1. Crea un fork del repositorio
2. Crea una rama para tu funcionalidad (`git checkout -b feature/nueva-funcionalidad`)
3. Haz commit de tus cambios (`git commit -m 'Añadir nueva funcionalidad'`)
4. Sube la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## Licencia

[MIT](LICENSE)
