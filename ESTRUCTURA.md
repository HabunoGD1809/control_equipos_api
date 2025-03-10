# Estructura del Proyecto: Sistema de Control de Equipos

```
control_equipos/
│
├── alembic/                       # Configuración y migraciones de base de datos
│   ├── versions/                  # Scripts de migración automáticamente generados
│   ├── env.py                     # Entorno de configuración para Alembic
│   ├── script.py.mako             # Plantilla para scripts de migración
│   └── README.md                  # Documentación de uso de Alembic
│
├── app/                           # Código fuente de la aplicación
│   ├── api/                       # Endpoints de la API
│   │   ├── routes/                # Rutas agrupadas por funcionalidad
│   │   │   ├── auth.py            # Autenticación y seguridad
│   │   │   ├── equipos.py         # Operaciones CRUD para equipos
│   │   │   ├── mantenimiento.py   # Gestión de mantenimientos
│   │   │   ├── movimientos.py     # Gestión de movimientos (entrada/salida)
│   │   │   └── usuarios.py        # Gestión de usuarios
│   │   ├── deps.py                # Dependencias para inyectar en rutas
│   │   └── __init__.py            # Registro de todas las rutas
│   │
│   ├── core/                      # Componentes principales
│   │   ├── error_handlers.py      # Manejadores de errores personalizados
│   │   ├── logging.py             # Configuración de logging
│   │   ├── security.py            # Autenticación JWT y hashing
│   │   ├── password.py            # Manejo de hashing y verificación de contraseñas con bcrypt
│   │   └── __init__.py            # Inicialización del módulo
│   │
│   ├── db/                        # Capa de acceso a datos
│   │   ├── models/                # Modelos SQLAlchemy
│   │   │   ├── equipos.py         # Modelos para equipos, estados, documentación
│   │   │   ├── mantenimiento.py   # Modelos para mantenimiento
│   │   │   ├── movimientos.py     # Modelos para movimientos
│   │   │   ├── usuarios.py        # Modelos para usuarios, roles y permisos
│   │   │   └── __init__.py        # Importación de todos los modelos
│   │   ├── base.py                # Modelo base con campos y métodos comunes
│   │   ├── session.py             # Gestión de conexiones a la base de datos
│   │   └── __init__.py            # Inicialización del módulo
│   │
│   ├── schemas/                   # Esquemas Pydantic (validación y serialización)
│   │   ├── common.py              # Esquemas comunes (paginación, respuestas)
│   │   ├── equipos.py             # Esquemas para equipos
│   │   ├── mantenimiento.py       # Esquemas para mantenimiento
│   │   ├── movimientos.py         # Esquemas para movimientos
│   │   ├── token.py               # Esquemas para autenticación
│   │   ├── usuarios.py            # Esquemas para usuarios
│   │   └── __init__.py            # Importación de todos los esquemas
│   │
│   ├── services/                  # Lógica de negocio
│   │   ├── equipos.py             # Servicios para equipos
│   │   ├── mantenimiento.py       # Servicios para mantenimiento
│   │   ├── movimientos.py         # Servicios para movimientos
│   │   ├── usuarios.py            # Servicios para usuarios
│   │   └── __init__.py            # Inicialización del módulo
│   │
│   ├── tasks/                     # Tareas en segundo plano
│   │   ├── maintenance.py         # Tareas de comprobación de mantenimientos
│   │   ├── notifications.py       # Tareas de envío de notificaciones
│   │   ├── reports.py             # Tareas de generación de reportes
│   │   └── __init__.py            # Registro de todas las tareas
│   │
│   ├── utils/                     # Funciones utilitarias
│   │   ├── helpers.py             # Funciones auxiliares
│   │   └── __init__.py            # Inicialización del módulo
│   │
│   ├── config.py                  # Configuración de la aplicación
│   ├── main.py                    # Punto de entrada de la aplicación
│   ├── worker.py                  # Procesador de tareas en segundo plano
│   └── __init__.py                # Inicialización del paquete
│
├── logs/                          # Directorio para archivos de log
│
├── reports/                       # Directorio para reportes generados
│
├── scripts/                       # Scripts utilitarios
│   └── start.sh                   # Script de inicio del contenedor
│
├── static/                        # Archivos estáticos (si es necesario)
│
├── tests/                         # Pruebas automatizadas
│   ├── api/                       # Pruebas para la API
│   │   ├── test_auth.py           # Pruebas de autenticación
│   │   ├── test_equipos.py        # Pruebas de equipos
│   │   ├── test_mantenimiento.py  # Pruebas de mantenimiento
│   │   ├── test_movimientos.py    # Pruebas de movimientos
│   │   ├── test_usuarios.py       # Pruebas de usuarios
│   │   └── __init__.py            # Inicialización del paquete
│   ├── conftest.py                # Configuración y fixtures para pruebas
│   └── __init__.py                # Inicialización del paquete
│
├── .env                           # Variables de entorno para desarrollo
├── .env.example                   # Ejemplo de variables de entorno
├── .gitignore                     # Archivos a ignorar por git
├── alembic.ini                    # Configuración de Alembic
├── docker-compose.yml             # Definición de servicios Docker
├── Dockerfile                     # Instrucciones para construir la imagen Docker
├── ESTRUCTURA.md                  # Este archivo, descripción de la estructura
├── pytest.ini                     # Configuración de pytest
├── README.md                      # Documentación principal del proyecto
└── requirements.txt               # Dependencias de Python
```

## Descripción de componentes principales

### API (app/api)
Contiene los endpoints de la API organizados por funcionalidad. Cada archivo en `routes/` define un conjunto de endpoints relacionados con una entidad específica (usuarios, equipos, etc.).

### Core (app/core)
Contiene la lógica central de la aplicación, incluyendo manejo de errores, configuración de logging, seguridad (autenticación y autorización), y funciones para el manejo seguro de contraseñas.

### DB (app/db)
Contiene los modelos SQLAlchemy que definen el esquema de la base de datos y la lógica para gestionar las conexiones.

### Schemas (app/schemas)
Define los esquemas Pydantic para validación de datos de entrada y salida de la API.

### Services (app/services)
Contiene la lógica de negocio de la aplicación, separada de los endpoints para facilitar la reutilización y testing.

### Tasks (app/tasks)
Define tareas que se ejecutan en segundo plano, como envío de notificaciones y generación de reportes.

### Alembic
Framework para migraciones de base de datos que permite evolucionar el esquema de manera controlada.

### Tests
Pruebas automatizadas para verificar el funcionamiento correcto de la aplicación.

### Docker
Archivos para containerizar la aplicación y sus dependencias, facilitando el despliegue en diferentes entornos.
