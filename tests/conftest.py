import asyncio
import sys
from typing import AsyncGenerator, Dict

import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.core.password import get_password_hash
from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app

# Configurar para evitar advertencias
def pytest_configure(config):
    config.option.asyncio_default_fixture_loop_scope = "function"

# Configuración de las URLs de la base de datos para tests
TEST_DB = "control_equipos_test_db"
TEST_DB_URL = str(settings.SQLALCHEMY_DATABASE_URI).replace(settings.POSTGRES_DB, TEST_DB)
POSTGRES_URL = str(settings.SQLALCHEMY_DATABASE_URI).replace(settings.POSTGRES_DB, "postgres")

# Configurar el loop en Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Función para crear la base de datos de prueba si no existe
async def ensure_test_database():
    """Crea la base de datos de prueba si no existe."""
    admin_engine = create_async_engine(POSTGRES_URL, isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as conn:
            result = await conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname='{TEST_DB}'")
            )
            database_exists = result.scalar() == 1
            if not database_exists:
                print(f"Creando base de datos de prueba '{TEST_DB}'...")
                await conn.execute(text(f'CREATE DATABASE "{TEST_DB}"'))
                print(f"Base de datos '{TEST_DB}' creada exitosamente.")
    finally:
        await admin_engine.dispose()

# Motor de base de datos global para tests
_test_engine = None

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Fixture para obtener el motor de BD de pruebas."""
    global _test_engine

    if _test_engine is not None:
        yield _test_engine
        return

    await ensure_test_database()

    _test_engine = create_async_engine(
        TEST_DB_URL,
        echo=False,
        future=True,
        connect_args={"options": f"-csearch_path={settings.POSTGRES_SCHEMA}"}
    )
    async with _test_engine.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.POSTGRES_SCHEMA}"))
        await conn.execute(text(f"SET search_path TO {settings.POSTGRES_SCHEMA}"))
        await conn.run_sync(Base.metadata.create_all)
    yield _test_engine

@pytest_asyncio.fixture
async def db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Fixture para obtener una sesión de BD para pruebas."""
    connection = await test_engine.connect()
    transaction = await connection.begin()

    session_factory = sessionmaker(
        bind=connection,
        expire_on_commit=False,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False
    )
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()

# Cliente asíncrono principal
@pytest_asyncio.fixture
async def async_client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Fixture para obtener un cliente de pruebas asíncrono."""
    # Override the dependency
    async def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Usar TestClient como base para el cliente asíncrono
    test_client = TestClient(app)
    
    # Crear una clase proxy para convertir el TestClient en AsyncClient
    class TestClientProxy(AsyncClient):
        async def request(self, method, url, **kwargs):
            # Usar TestClient para las peticiones reales
            response = getattr(test_client, method.lower())(url, **kwargs)
            return response
    
    # Crear el cliente con la URL base
    async with TestClientProxy(base_url="http://testserver") as ac:
        yield ac
    
    app.dependency_overrides.clear()

# Cliente para compatibilidad con tests existentes
@pytest_asyncio.fixture
async def client(async_client: AsyncClient) -> AsyncClient: # type: ignore
    """Alias para async_client para compatibilidad con pruebas existentes."""
    yield async_client

@pytest_asyncio.fixture
async def admin_token(db: AsyncSession) -> Dict[str, str]:
    """Fixture para generar token de administrador."""
    from app.db.models import Usuario, Rol
    from app.core.password import get_password_hash
    
    # Crear rol de administrador
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

    access_token = create_access_token(subject=admin_user.nombre_usuario)
    return {"Authorization": f"Bearer {access_token}"}

@pytest_asyncio.fixture
async def user_token(db: AsyncSession) -> Dict[str, str]:
    """Fixture para generar token de usuario regular."""
    from app.db.models import Usuario, Rol
    
    # Crear rol de usuario
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

    access_token = create_access_token(subject=regular_user.nombre_usuario)
    return {"Authorization": f"Bearer {access_token}"}
