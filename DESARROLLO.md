# Guía de Desarrollo

Este documento proporciona información detallada para desarrolladores que quieran mantener o extender el Sistema de Control de Equipos.

## Entorno de Desarrollo

### Configuración recomendada

1. **Editor/IDE**:
   - VS Code con extensiones para Python, FastAPI y PostgreSQL
   - PyCharm Professional (con soporte para bases de datos)

2. **Herramientas de desarrollo**:
   - Black: Formateador de código
   - Flake8: Linter para detectar problemas
   - Mypy: Verificación de tipos estáticos
   - Pytest: Framework para pruebas
   - Pre-commit: Hooks para validar cambios antes de commit

### Dependencias de desarrollo

Instala las dependencias de desarrollo adicionales:

```bash
pip install -r requirements-dev.txt
```

## Arquitectura de la Aplicación

La aplicación sigue una arquitectura en capas:

1. **API Routes** (Controladores): Manejan las peticiones HTTP
2. **Services** (Servicios): Contienen la lógica de negocio
3. **Models** (Modelos): Representan las entidades de la base de datos
4. **Schemas** (Esquemas): Validan datos de entrada/salida
5. **Workers**: Procesan tareas asíncronas

### Flujo de datos

```
Cliente HTTP → API Routes → Services → Models → Base de datos
                ↑             ↑          ↓
              Schemas ←────── ┘          ↓
                ↑                        ↓
                └─────────────────────── ┘
```

## Patrones y Convenciones

### Nombrado

- **Archivos**: Usar snake_case (ej: `user_service.py`)
- **Clases**: Usar PascalCase (ej: `UserService`)
- **Funciones/variables**: Usar snake_case (ej: `get_user_by_id`)
- **Constantes**: Usar UPPER_SNAKE_CASE (ej: `MAX_LOGIN_ATTEMPTS`)

### Estructura de Endpoints

Seguimos una estructura RESTful:

- `GET /resource`: Listar recursos
- `POST /resource`: Crear recurso
- `GET /resource/{id}`: Obtener un recurso
- `PUT /resource/{id}`: Actualizar recurso
- `DELETE /resource/{id}`: Eliminar recurso
- `POST /resource/{id}/action`: Acciones especiales

### Manejo de Errores

- Usar las clases de error definidas en `core/error_handlers.py`
- No exponer información sensible en mensajes de error
- Loguear errores con niveles apropiados

## Base de Datos

### Modelado

- Usar UUID como clave primaria
- Incluir campos de auditoría (created_at, updated_at)
- Definir restricciones a nivel de base de datos

### Migraciones

1. Modifica los modelos SQLAlchemy en `app/db/models/`
2. Genera la migración:
   ```bash
   alembic revision --autogenerate -m "descripción del cambio"
   ```
3. Revisa y edita el archivo generado en `alembic/versions/`
4. Aplica la migración:
   ```bash
   alembic upgrade head
   ```

## Autenticación y Seguridad

### JWT

- Los tokens JWT se generan al iniciar sesión
- Contienen el nombre de usuario como subject
- Tienen una expiración configurable (por defecto 8 días)

### Roles y Permisos

- Usar los decoradores de `api/deps.py` para proteger endpoints
- Ejemplo: `@Depends(get_current_user_with_permissions(["ver_equipos"]))`

## Tareas en Segundo Plano

### Worker

El sistema incluye un worker para tareas asíncronas:

1. Define una tarea en un módulo dentro de `app/tasks/`
2. Usa el decorador `@register_task("nombre_tarea")`
3. Encola la tarea con `await enqueue_task("nombre_tarea", arg1, arg2)`

### Tareas Programadas

Para tareas recurrentes, puedes usar pgAgent en PostgreSQL o configurar un cronjob que envíe peticiones al API endpoint correspondiente.

## Pruebas

### Estructura

- Pruebas unitarias: Prueban una función o clase específica
- Pruebas de integración: Prueban la interacción entre componentes
- Pruebas de API: Prueban endpoints completos

### Fixtures

En `tests/conftest.py` hay fixtures para:
- Crear una base de datos de prueba
- Obtener un cliente HTTP para pruebas
- Obtener tokens de autenticación de prueba

### Ejecución

```bash
# Ejecutar todas las pruebas
pytest

# Ejecutar un archivo específico
pytest tests/api/test_auth.py

# Ejecutar con cobertura
pytest --cov=app

# Generar reporte HTML de cobertura
pytest --cov=app --cov-report=html
```

## Extensión del Sistema

### Añadir un Nuevo Módulo

1. Crear modelos en `app/db/models/`
2. Generar migración con Alembic
3. Crear esquemas en `app/schemas/`
4. Implementar servicios en `app/services/`
5. Crear endpoints en `app/api/routes/`
6. Registrar rutas en `app/api/routes/__init__.py`
7. Añadir pruebas en `tests/`

### Implementar un Nuevo Tipo de Reporte

1. Crear función en `app/tasks/reports.py`
2. Registrarla con `@register_task("nombre_reporte")`
3. Añadir endpoint para solicitar el reporte

## Rendimiento y Optimización

### Paginación

Todos los endpoints que devuelven listas deben implementar paginación:
- Usar parámetros `skip` y `limit`
- Devolver metadatos de paginación (total, página actual)

### Consultas Optimizadas

- Usar `select()` con joins explícitos
- Usar `options(joinedload())` para cargar relaciones eficientemente
- Evitar N+1 queries

### Caché

Para datos que cambian poco, considera implementar caché con:
- Redis (para producción)
- En memoria (para desarrollo)

## Proceso de Cambios

### Workflow

1. Crear una rama desde `main`
2. Implementar cambios con commits atómicos
3. Escribir o actualizar pruebas
4. Verificar el linting y la cobertura
5. Crear un Pull Request
6. Revisar y aprobar el PR
7. Merge a `main`

### Commit Messages

Seguir el formato:
```
tipo(alcance): resumen

descripción detallada
```

Tipos: feat, fix, docs, style, refactor, test, chore

## Despliegue

### Versiones

Seguimos Semantic Versioning (MAJOR.MINOR.PATCH):
- MAJOR: Cambios incompatibles con versiones anteriores
- MINOR: Nuevas funcionalidades compatibles
- PATCH: Correcciones de errores compatibles

### Entornos

- **dev**: Para desarrollo y pruebas internas
- **stage**: Para pruebas de integración previas a producción
- **prod**: Entorno de producción

## Soporte

Para preguntas o problemas, contacta al equipo de desarrollo a través de:
- GitHub Issues
- Email: soporte@ejemplo.com
