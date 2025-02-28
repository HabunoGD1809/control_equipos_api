import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Equipo, EstadoEquipo, Proveedor


@pytest.mark.asyncio
async def test_create_equipo(client: AsyncClient, db: AsyncSession, admin_token: dict):
    """Probar creación de equipo"""
    # Crear estado de equipo
    estado = EstadoEquipo(
        nombre="disponible", 
        descripcion="Equipo disponible", 
        permite_movimientos=True
    )
    db.add(estado)
    await db.commit()
    await db.refresh(estado)
    
    # Crear proveedor
    proveedor = Proveedor(
        nombre="Proveedor Test", 
        descripcion="Proveedor para pruebas",
        contacto="contacto@proveedor.com"
    )
    db.add(proveedor)
    await db.commit()
    await db.refresh(proveedor)
    
    # Datos para crear equipo
    equipo_data = {
        "nombre": "Equipo de prueba",
        "numero_serie": "ABCDE-12345-XYZ",
        "estado_id": str(estado.id),
        "ubicacion_actual": "Oficina de pruebas",
        "marca": "Marca Test",
        "modelo": "Modelo Test",
        "fecha_adquisicion": str(date.today()),
        "proveedor_id": str(proveedor.id),
        "notas": "Equipo creado para pruebas"
    }
    
    # Crear equipo
    response = await client.post(
        "/api/v1/equipos/",
        json=equipo_data,
        headers=admin_token
    )
    
    # Verificar respuesta
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["message"] == "Equipo creado correctamente"
    
    # Verificar que se creó en la BD
    equipo_id = uuid.UUID(data["id"])
    db_equipo = await db.get(Equipo, equipo_id)
    assert db_equipo is not None
    assert db_equipo.nombre == equipo_data["nombre"]
    assert db_equipo.numero_serie == equipo_data["numero_serie"]


@pytest.mark.asyncio
async def test_get_equipos(client: AsyncClient, db: AsyncSession, admin_token: dict):
    """Probar obtención de lista de equipos"""
    # Crear estado de equipo
    estado = EstadoEquipo(
        nombre="disponible", 
        descripcion="Equipo disponible", 
        permite_movimientos=True
    )
    db.add(estado)
    await db.commit()
    await db.refresh(estado)
    
    # Crear varios equipos
    equipos = []
    for i in range(3):
        equipo = Equipo(
            nombre=f"Equipo {i}",
            numero_serie=f"TEST{i}-12345-XYZ",
            estado_id=estado.id,
            ubicacion_actual="Ubicación de prueba",
            marca="Marca Test",
            modelo="Modelo Test"
        )
        db.add(equipo)
        equipos.append(equipo)
    
    await db.commit()
    
    # Obtener lista de equipos
    response = await client.get(
        "/api/v1/equipos/",
        headers=admin_token
    )
    
    # Verificar respuesta
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 3


@pytest.mark.asyncio
async def test_get_equipo_by_id(client: AsyncClient, db: AsyncSession, admin_token: dict):
    """Probar obtención de equipo por ID"""
    # Crear estado de equipo
    estado = EstadoEquipo(
        nombre="disponible", 
        descripcion="Equipo disponible", 
        permite_movimientos=True
    )
    db.add(estado)
    await db.commit()
    await db.refresh(estado)
    
    # Crear equipo
    equipo = Equipo(
        nombre="Equipo para buscar",
        numero_serie="FIND1-12345-XYZ",
        estado_id=estado.id,
        ubicacion_actual="Ubicación de prueba",
        marca="Marca Test",
        modelo="Modelo Test"
    )
    db.add(equipo)
    await db.commit()
    await db.refresh(equipo)
    
    # Obtener equipo por ID
    response = await client.get(
        f"/api/v1/equipos/{equipo.id}",
        headers=admin_token
    )
    
    # Verificar respuesta
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["data"]["id"] == str(equipo.id)
    assert data["data"]["nombre"] == equipo.nombre
    assert data["data"]["numero_serie"] == equipo.numero_serie


@pytest.mark.asyncio
async def test_update_equipo(client: AsyncClient, db: AsyncSession, admin_token: dict):
    """Probar actualización de equipo"""
    # Crear estado de equipo
    estado = EstadoEquipo(
        nombre="disponible", 
        descripcion="Equipo disponible", 
        permite_movimientos=True
    )
    db.add(estado)
    await db.commit()
    await db.refresh(estado)
    
    # Crear equipo
    equipo = Equipo(
        nombre="Equipo para actualizar",
        numero_serie="UPDT1-12345-XYZ",
        estado_id=estado.id,
        ubicacion_actual="Ubicación original",
        marca="Marca Original",
        modelo="Modelo Original"
    )
    db.add(equipo)
    await db.commit()
    await db.refresh(equipo)
    
    # Datos para actualizar
    update_data = {
        "nombre": "Equipo actualizado",
        "ubicacion_actual": "Nueva ubicación",
        "modelo": "Modelo Actualizado"
    }
    
    # Actualizar equipo
    response = await client.put(
        f"/api/v1/equipos/{equipo.id}",
        json=update_data,
        headers=admin_token
    )
    
    # Verificar respuesta
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(equipo.id)
    assert data["message"] == "Equipo actualizado correctamente"
    
    # Verificar que se actualizó en la BD
    await db.refresh(equipo)
    assert equipo.nombre == update_data["nombre"]
    assert equipo.ubicacion_actual == update_data["ubicacion_actual"]
    assert equipo.modelo == update_data["modelo"]


@pytest.mark.asyncio
async def test_delete_equipo(client: AsyncClient, db: AsyncSession, admin_token: dict):
    """Probar eliminación de equipo"""
    # Crear estado de equipo
    estado = EstadoEquipo(
        nombre="disponible", 
        descripcion="Equipo disponible", 
        permite_movimientos=True
    )
    db.add(estado)
    await db.commit()
    await db.refresh(estado)
    
    # Crear equipo
    equipo = Equipo(
        nombre="Equipo para eliminar",
        numero_serie="DEL01-12345-XYZ",
        estado_id=estado.id,
        ubicacion_actual="Ubicación de prueba",
        marca="Marca Test",
        modelo="Modelo Test"
    )
    db.add(equipo)
    await db.commit()
    await db.refresh(equipo)
    
    # Eliminar equipo
    response = await client.delete(
        f"/api/v1/equipos/{equipo.id}",
        headers=admin_token
    )
    
    # Verificar respuesta
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(equipo.id)
    assert data["message"] == "Equipo eliminado correctamente"
    
    # Verificar que se eliminó de la BD
    db_equipo = await db.get(Equipo, equipo.id)
    assert db_equipo is None
