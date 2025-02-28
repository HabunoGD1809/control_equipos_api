from datetime import datetime
from fastapi import APIRouter, Body, Depends, Path, Query, status
import uuid
from typing import Any, List, Optional

from app.api.deps import (
    CurrentUser, DbSession,
    MantenimientosReadUser, MantenimientosWriteUser
)
from app.core.error_handlers import NotFoundError, BadRequestError
from app.schemas.common import (
    ItemCreatedResponse, ItemDeletedResponse, 
    ItemResponse, ItemsResponse, ItemUpdatedResponse, 
    Mensaje, PaginatedResponse
)
from app.schemas.mantenimiento import (
    Mantenimiento, MantenimientoBase, MantenimientoConDetalles, 
    MantenimientoCreate, MantenimientoEstado, MantenimientoUpdate,
    TipoMantenimiento, TipoMantenimientoBase, TipoMantenimientoCreate, TipoMantenimientoUpdate
)
from app.services.mantenimiento import (
    cambiar_estado_mantenimiento, create_mantenimiento, create_tipo_mantenimiento,
    delete_mantenimiento, delete_tipo_mantenimiento, 
    get_mantenimiento, get_mantenimientos, get_proximos_mantenimientos,
    get_tipo_mantenimiento, get_tipos_mantenimiento,
    update_mantenimiento, update_tipo_mantenimiento
)

router = APIRouter()


# Rutas para Tipos de Mantenimiento
@router.get("/tipos", response_model=ItemsResponse[TipoMantenimiento])
async def list_tipos_mantenimiento(
    db: DbSession,
    current_user: MantenimientosReadUser
) -> Any:
    """
    Obtiene todos los tipos de mantenimiento disponibles.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
    """
    tipos = await get_tipos_mantenimiento(db)
    
    return ItemsResponse(data=tipos)


@router.post("/tipos", response_model=ItemCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_tipo_mantenimiento_route(
    db: DbSession,
    current_user: MantenimientosWriteUser,
    tipo_in: TipoMantenimientoCreate = Body(...)
) -> Any:
    """
    Crea un nuevo tipo de mantenimiento.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        tipo_in: Datos del tipo de mantenimiento a crear
    """
    tipo = await create_tipo_mantenimiento(db, tipo_in)
    
    return ItemCreatedResponse(
        id=tipo["id"],
        message="Tipo de mantenimiento creado correctamente"
    )


@router.get("/tipos/{tipo_id}", response_model=ItemResponse[TipoMantenimiento])
async def get_tipo_mantenimiento_by_id(
    db: DbSession,
    current_user: MantenimientosReadUser,
    tipo_id: uuid.UUID = Path(...)
) -> Any:
    """
    Obtiene un tipo de mantenimiento por su ID.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        tipo_id: ID del tipo de mantenimiento
    """
    tipo = await get_tipo_mantenimiento(db, tipo_id)
    
    if not tipo:
        raise NotFoundError("Tipo de mantenimiento no encontrado")
    
    return ItemResponse(data=tipo)


@router.put("/tipos/{tipo_id}", response_model=ItemUpdatedResponse)
async def update_tipo_mantenimiento_route(
    db: DbSession,
    current_user: MantenimientosWriteUser,
    tipo_id: uuid.UUID = Path(...),
    tipo_in: TipoMantenimientoUpdate = Body(...)
) -> Any:
    """
    Actualiza un tipo de mantenimiento existente.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        tipo_id: ID del tipo de mantenimiento a actualizar
        tipo_in: Datos actualizados del tipo de mantenimiento
    """
    tipo = await get_tipo_mantenimiento(db, tipo_id)
    
    if not tipo:
        raise NotFoundError("Tipo de mantenimiento no encontrado")
    
    tipo_actualizado = await update_tipo_mantenimiento(db, tipo_id, tipo_in)
    
    return ItemUpdatedResponse(
        id=tipo_id,
        message="Tipo de mantenimiento actualizado correctamente"
    )


@router.delete("/tipos/{tipo_id}", response_model=ItemDeletedResponse)
async def delete_tipo_mantenimiento_route(
    db: DbSession,
    current_user: MantenimientosWriteUser,
    tipo_id: uuid.UUID = Path(...)
) -> Any:
    """
    Elimina un tipo de mantenimiento.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        tipo_id: ID del tipo de mantenimiento a eliminar
    """
    try:
        eliminado = await delete_tipo_mantenimiento(db, tipo_id)
        
        if not eliminado:
            raise NotFoundError("Tipo de mantenimiento no encontrado")
        
        return ItemDeletedResponse(
            id=tipo_id,
            message="Tipo de mantenimiento eliminado correctamente"
        )
    except BadRequestError as e:
        raise e


# Rutas para Mantenimientos
@router.get("/", response_model=PaginatedResponse[MantenimientoConDetalles])
async def list_mantenimientos(
    db: DbSession,
    current_user: MantenimientosReadUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    equipo_id: Optional[uuid.UUID] = None,
    tipo_id: Optional[uuid.UUID] = None,
    estado: Optional[str] = Query(None, pattern=r'^(programado|en_proceso|completado|cancelado)$'),
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None,
    vencidos: Optional[bool] = Query(False)
) -> Any:
    """
    Obtiene la lista de mantenimientos con filtros opcionales.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        skip: Número de registros a omitir (paginación)
        limit: Límite de registros a devolver
        equipo_id: Filtrar por equipo
        tipo_id: Filtrar por tipo de mantenimiento
        estado: Filtrar por estado
        desde: Filtrar por fecha desde
        hasta: Filtrar por fecha hasta
        vencidos: Filtrar solo vencidos
    """
    mantenimientos = await get_mantenimientos(
        db, skip=skip, limit=limit, 
        equipo_id=equipo_id, tipo_id=tipo_id, estado=estado,
        desde=desde, hasta=hasta, vencidos=vencidos
    )
    
    # Obtener total para paginación
    # (Deberia ser una consulta separada de count)
    total = len(await get_mantenimientos(db)) if not any([equipo_id, tipo_id, estado, desde, hasta, vencidos]) else len(mantenimientos)
    
    return PaginatedResponse.create(
        items=mantenimientos,
        total=total,
        page=(skip // limit) + 1,
        size=limit
    )


@router.post("/", response_model=ItemCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_mantenimiento_route(
    db: DbSession,
    current_user: MantenimientosWriteUser,
    mantenimiento_in: MantenimientoCreate = Body(...)
) -> Any:
    """
    Programa un nuevo mantenimiento.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        mantenimiento_in: Datos del mantenimiento a crear
    """
    mantenimiento = await create_mantenimiento(db, mantenimiento_in)
    
    return ItemCreatedResponse(
        id=mantenimiento["id"],
        message="Mantenimiento programado correctamente"
    )


@router.get("/{mantenimiento_id}", response_model=ItemResponse[MantenimientoConDetalles])
async def get_mantenimiento_by_id(
    db: DbSession,
    current_user: MantenimientosReadUser,
    mantenimiento_id: uuid.UUID = Path(...)
) -> Any:
    """
    Obtiene un mantenimiento por su ID.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        mantenimiento_id: ID del mantenimiento
    """
    mantenimiento = await get_mantenimiento(db, mantenimiento_id)
    
    if not mantenimiento:
        raise NotFoundError("Mantenimiento no encontrado")
    
    return ItemResponse(data=mantenimiento)


@router.put("/{mantenimiento_id}", response_model=ItemUpdatedResponse)
async def update_mantenimiento_route(
    db: DbSession,
    current_user: MantenimientosWriteUser,
    mantenimiento_id: uuid.UUID = Path(...),
    mantenimiento_in: MantenimientoUpdate = Body(...)
) -> Any:
    """
    Actualiza un mantenimiento existente.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        mantenimiento_id: ID del mantenimiento a actualizar
        mantenimiento_in: Datos actualizados del mantenimiento
    """
    mantenimiento = await get_mantenimiento(db, mantenimiento_id)
    
    if not mantenimiento:
        raise NotFoundError("Mantenimiento no encontrado")
    
    # Verificar que el mantenimiento no esté completado o cancelado
    if mantenimiento["estado"] in ["completado", "cancelado"]:
        raise BadRequestError("No se puede modificar un mantenimiento completado o cancelado")
    
    mantenimiento_actualizado = await update_mantenimiento(db, mantenimiento_id, mantenimiento_in)
    
    return ItemUpdatedResponse(
        id=mantenimiento_id,
        message="Mantenimiento actualizado correctamente"
    )


@router.delete("/{mantenimiento_id}", response_model=ItemDeletedResponse)
async def delete_mantenimiento_route(
    db: DbSession,
    current_user: MantenimientosWriteUser,
    mantenimiento_id: uuid.UUID = Path(...)
) -> Any:
    """
    Elimina un mantenimiento.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        mantenimiento_id: ID del mantenimiento a eliminar
    """
    eliminado = await delete_mantenimiento(db, mantenimiento_id)
    
    if not eliminado:
        raise NotFoundError("Mantenimiento no encontrado")
    
    return ItemDeletedResponse(
        id=mantenimiento_id,
        message="Mantenimiento eliminado correctamente"
    )


@router.post("/{mantenimiento_id}/estado", response_model=ItemUpdatedResponse)
async def cambiar_estado_mantenimiento_route(
    db: DbSession,
    current_user: MantenimientosWriteUser,
    mantenimiento_id: uuid.UUID = Path(...),
    estado_in: MantenimientoEstado = Body(...)
) -> Any:
    """
    Cambia el estado de un mantenimiento.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        mantenimiento_id: ID del mantenimiento
        estado_in: Datos del nuevo estado
    """
    mantenimiento = await get_mantenimiento(db, mantenimiento_id)
    
    if not mantenimiento:
        raise NotFoundError("Mantenimiento no encontrado")
    
    # Verificar que el mantenimiento no esté completado o cancelado
    if mantenimiento["estado"] in ["completado", "cancelado"]:
        raise BadRequestError("No se puede cambiar el estado de un mantenimiento completado o cancelado")
    
    mantenimiento_actualizado = await cambiar_estado_mantenimiento(
        db, mantenimiento_id, estado_in.estado, 
        estado_in.observaciones, estado_in.costo
    )
    
    return ItemUpdatedResponse(
        id=mantenimiento_id,
        message=f"Estado de mantenimiento actualizado a '{estado_in.estado}' correctamente"
    )


@router.get("/reportes/proximos", response_model=ItemsResponse[MantenimientoConDetalles])
async def get_proximos_mantenimientos_route(
    db: DbSession,
    current_user: MantenimientosReadUser,
    dias: int = Query(30, ge=1, le=365)
) -> Any:
    """
    Obtiene los mantenimientos programados para los próximos días.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        dias: Número de días a considerar
    """
    mantenimientos = await get_proximos_mantenimientos(db, dias)
    
    return ItemsResponse(data=mantenimientos)
