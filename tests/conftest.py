import asyncio
import os
from typing import AsyncGenerator, Dict

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app

# Sobreescribir configuración para tests
TEST_DB = "control_equipos_test_db"
TEST_DB_URL = str(settings.SQLALCHEMY_DATABASE_URI).replace(
    settings.POSTGRES_DB, TEST_DB
)

# Crear engine para tests
test_engine = create_async_engine(
    TEST_DB_URL,
    echo=False,
    future=True,
    connect_args={"options": f"-csearch_path={settings.POSTGRES_SCHEMA}"}
)

# Session factory para tests
TestingSessionLocal = sessionmaker(
    test_engine, 
    expire_on_commit=False, 
    class_=AsyncSession, 
    autocommit=False, 
    autoflush=False
)


@pytest.fixture(scope="session")
def event_loop():
    """
    Evento de bucle para pruebas asíncronas.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db() -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture para obtener una sesión de BD para pruebas.
    """
    connection = await test_engine.connect()
    transaction = await connection.begin()
    
    # Crear esquema si no existe
    await connection.execute(f"CREATE SCHEMA IF NOT EXISTS {settings.POSTGRES_SCHEMA}")
    await connection.execute(f"SET search_path TO {settings.POSTGRES_SCHEMA}")
    
    # Crear tablas
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = TestingSessionLocal(bind=connection)
    
    try:
        yield async_session
    finally:
        await async_session.close()
        await transaction.rollback()
        await connection.close()


@pytest_asyncio.fixture(scope="function")
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Fixture para obtener un cliente de pruebas.
    """
    # Sobreescribir la dependencia de base de datos
    async def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def admin_token(db: AsyncSession) -> Dict[str, str]:
    """
    Fixture para obtener un token de administrador para pruebas.
    """
    from app.db.models import Usuario, Rol
    from app.core.security import get_password_hash
    
    # Crear rol de administrador si no existe
    admin_role = Rol(nombre="admin", descripcion="Administrador del sistema")
    db.add(admin_role)
    await db.commit()
    await db.refresh(admin_role)
    
    # Crear usuario administrador
    admin_user = Usuario(
        nombre_usuario="admin_test",
        contrasena=get_password_hash("admin123"),
        rol_id=admin_role.id,
        email="admin@test.com",
        requiere_cambio_contrasena=False
    )
    db.add(admin_user)
    await db.commit()
    
    # Generar token
    access_token = create_access_token(subject=admin_user.nombre_usuario)
    
    return {"Authorization": f"Bearer {access_token}"}


@pytest_asyncio.fixture(scope="function")
async def user_token(db: AsyncSession) -> Dict[str, str]:
    """
    Fixture para obtener un token de usuario regular para pruebas.
    """
    from app.db.models import Usuario, Rol
    from app.core.password import get_password_hash
    
    # Crear rol de usuario si no existe
    user_role = Rol(nombre="usuario", descripcion="Usuario estándar")
    db.add(user_role)
    await db.commit()
    await db.refresh(user_role)
    
    # Crear usuario regular
    regular_user = Usuario(
        nombre_usuario="user_test",
        contrasena=get_password_hash("user123"),
        rol_id=user_role.id,
        email="user@test.com",
        requiere_cambio_contrasena=False
    )
    db.add(regular_user)
    await db.commit()
    
    # Generar token
    access_token = create_access_token(subject=regular_user.nombre_usuario)
    
    return {"Authorization": f"Bearer {access_token}"}
