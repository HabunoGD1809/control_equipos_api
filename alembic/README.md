# Gestión de migraciones con Alembic

Este directorio contiene la configuración para Alembic, una herramienta para gestionar migraciones de base de datos.

## Comandos útiles de Alembic

### Crear una nueva migración

```bash
alembic revision --autogenerate -m "descripción de la migración"
```

Este comando:
- Detecta cambios en tus modelos SQLAlchemy
- Genera un script de migración con los cambios necesarios

### Aplicar migraciones pendientes

```bash
alembic upgrade head
```

Este comando:
- Aplica todas las migraciones pendientes hasta la última versión

### Aplicar una migración específica

```bash
alembic upgrade +1  # Aplicar una migración adelante
alembic upgrade <revision>  # Aplicar hasta una revisión específica
```

### Revertir migraciones

```bash
alembic downgrade -1  # Revertir una migración
alembic downgrade <revision>  # Revertir hasta una revisión específica
alembic downgrade base  # Revertir todas las migraciones
```

### Ver el historial de migraciones

```bash
alembic history --verbose
```

### Mostrar la versión actual

```bash
alembic current
```

## Estructura de directorios

- `versions/`: Contiene los archivos de migración generados
- `env.py`: Configuración del entorno de Alembic
- `script.py.mako`: Plantilla para generar archivos de migración

## Consideraciones importantes

1. **Siempre revise los scripts generados antes de aplicarlos en producción**
2. **Mantenga el control de versiones de sus migraciones junto con su código**
3. **Evite modificar migraciones que ya han sido aplicadas en cualquier entorno**
