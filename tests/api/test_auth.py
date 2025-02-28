import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.password import get_password_hash
from app.db.models import Usuario, Rol


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db: AsyncSession):
    """Probar login exitoso"""
    # Crear rol si no existe
    user_role = Rol(nombre="usuario", descripcion="Usuario estándar")
    db.add(user_role)
    await db.commit()
    await db.refresh(user_role)
    
    # Crear usuario de prueba
    username = "testuser"
    password = "testpassword"
    test_user = Usuario(
        nombre_usuario=username,
        contrasena=get_password_hash(password),
        rol_id=user_role.id,
        email="test@example.com",
        requiere_cambio_contrasena=False
    )
    db.add(test_user)
    await db.commit()
    
    # Realizar login
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password}
    )
    
    # Verificar respuesta
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, db: AsyncSession):
    """Probar login con contraseña incorrecta"""
    # Crear rol si no existe
    user_role = Rol(nombre="usuario", descripcion="Usuario estándar")
    db.add(user_role)
    await db.commit()
    await db.refresh(user_role)
    
    # Crear usuario de prueba
    username = "testuser2"
    password = "correctpassword"
    test_user = Usuario(
        nombre_usuario=username,
        contrasena=get_password_hash(password),
        rol_id=user_role.id,
        email="test2@example.com",
        requiere_cambio_contrasena=False
    )
    db.add(test_user)
    await db.commit()
    
    # Realizar login con contraseña incorrecta
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "wrongpassword"}
    )
    
    # Verificar respuesta
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "Credenciales incorrectas" in data["detail"]


@pytest.mark.asyncio
async def test_login_user_not_found(client: AsyncClient):
    """Probar login con usuario inexistente"""
    # Realizar login con usuario inexistente
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "nonexistentuser", "password": "anypassword"}
    )
    
    # Verificar respuesta
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "Credenciales incorrectas" in data["detail"]


@pytest.mark.asyncio
async def test_login_blocked_user(client: AsyncClient, db: AsyncSession):
    """Probar login con usuario bloqueado"""
    # Crear rol si no existe
    user_role = Rol(nombre="usuario", descripcion="Usuario estándar")
    db.add(user_role)
    await db.commit()
    await db.refresh(user_role)
    
    # Crear usuario bloqueado
    username = "blockeduser"
    password = "testpassword"
    test_user = Usuario(
        nombre_usuario=username,
        contrasena=get_password_hash(password),
        rol_id=user_role.id,
        email="blocked@example.com",
        bloqueado=True,
        requiere_cambio_contrasena=False
    )
    db.add(test_user)
    await db.commit()
    
    # Realizar login con usuario bloqueado
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password}
    )
    
    # Verificar respuesta
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data
    assert "Usuario bloqueado" in data["detail"]
