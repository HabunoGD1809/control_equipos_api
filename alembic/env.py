import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import settings
from app.db.base import Base
from app.db.models import *  # Importar todos los modelos para que Alembic los detecte

# Esta es la configuración de Alembic que se usa para autogenerar migraciones
config = context.config

# Leer la configuración del archivo alembic.ini
fileConfig(config.config_file_name)

# Establecer el objeto MetaData para detectar cambios en los modelos
target_metadata = Base.metadata

# Establecer el esquema de la base de datos
def context_configure_callback(config, connection, target_metadata):
    config.set_main_option("sqlalchemy.schema", "control_equipos")

# Sobreescribir la URL de la base de datos con la configuración de la aplicación
config.set_main_option(
    "sqlalchemy.url", 
    str(settings.SQLALCHEMY_DATABASE_URI).replace("+psycopg", "")
)
config.set_main_option("sqlalchemy.url.query", f"options=-c search_path={settings.POSTGRES_SCHEMA}")


def run_migrations_offline() -> None:
    """
    Ejecuta migraciones en modo 'offline'
    
    Esto configura el contexto con solo una URL y no un motor, aunque en realidad, 
    nunca utiliza dicha URL para conexiones dado que el modo 'offline' no ejecuta ninguna acción
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Ejecuta migraciones en un contexto
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        version_table_schema=settings.POSTGRES_SCHEMA,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Ejecuta migraciones en modo 'online'
    """
    # Crear el motor usando la configuración del INI con la URL de la app
    connectable = AsyncEngine(
        engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )
    )

    async with connectable.connect() as connection:
        await connection.execute(f'CREATE SCHEMA IF NOT EXISTS {settings.POSTGRES_SCHEMA}')
        await connection.execute(f'SET search_path TO {settings.POSTGRES_SCHEMA}')
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
