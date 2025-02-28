from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession, 
    async_sessionmaker, 
    create_async_engine
)
from sqlalchemy.orm import declarative_base

from app.config import settings

# Configuración de logging
logger = logging.getLogger(__name__)

# Engine de SQLAlchemy para conexiones asíncronas
engine = create_async_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),  # Convert a str
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,
    echo_pool=False,
    pool_recycle=3600,  # Reciclar conexiones después de una hora
    connect_args={"options": f"-csearch_path={settings.POSTGRES_SCHEMA}"}
)

# Factory de sesiones
async_session_factory = async_sessionmaker(
    engine, 
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base para modelos declarativos
Base = declarative_base()

# Contexto asíncrono para manejo de sesiones de BD
@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Contexto asíncrono para manejo de sesiones de base de datos.
    Garantiza que la sesión se cierre correctamente después de su uso.
    """
    session: Optional[AsyncSession] = None
    try:
        session = async_session_factory()
        logger.debug("DB session created")
        yield session
    except Exception as e:
        logger.error(f"Error en sesión de base de datos: {str(e)}")
        if session:
            await session.rollback()
        raise
    finally:
        if session:
            await session.close()
            logger.debug("DB session closed")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependencia para inyectar sesiones de base de datos en los endpoints de FastAPI.
    """
    async with get_db_context() as session:
        yield session
