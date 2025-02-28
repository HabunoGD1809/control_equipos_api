from datetime import datetime
from fastapi import APIRouter, Body, Depends, Path, Query, status
import uuid
from typing import Any, List, Optional

from app.api.deps import (
    CurrentUser, DbSession,
    MovimientosAuthUser, MovimientosUser
)
from app.core.error_handlers import NotFoundError, BadRequestError
from app.schemas.common import (
    ItemCreatedResponse, ItemDeletedResponse, 
    ItemResponse, ItemsResponse, ItemUpdatedResponse, 
    Mensaje, PaginatedResponse
)
from app.schemas.movimientos import (
    Movimiento, MovimientoAutorizar, MovimientoBase, MovimientoCancelar, 
    MovimientoConDetalles, MovimientoCreate, MovimientoRetorno, MovimientoUpdate
)
from app.services.movimientos import (
    autorizar_movimiento, cancelar_movimiento, create_movimiento, 
    get_movimiento, get_movimientos, get_movimientos_vencidos, 
    registrar_retorno, update_movimiento
)

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[MovimientoConDetalles])
async def list_movimientos(
    db: DbSession,
    current_user: MovimientosUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    equipo_id: Optional[uuid.UUID] = None,
    usuario_id: Optional[uuid.UUID] = None,
    tipo_movimiento: Optional[str] = Query(None, pattern=r'^(salida|entrada)$'),
    estado: Optional[str] = Query(None, pattern=r'^(pendiente|en_proceso|completado|cancelado)$'),
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None
) -> Any:
    """
    Obtiene la lista de movimientos con filtros opcionales.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        skip: Número de registros a omitir (paginación)
        limit: Límite de registros a devolver
        equipo_id: Filtrar por equipo
        usuario_id: Filtrar por usuario
        tipo_movimiento: Filtrar por tipo de movimiento
        estado: Filtrar por estado
        desde: Filtrar por fecha desde
        hasta: Filtrar por fecha hasta
    """
    movimientos = await get_movimientos(
        db, skip=skip, limit=limit, 
        equipo_id=equipo_id, usuario_id=usuario_id,
        tipo_movimiento=tipo_movimiento, estado=estado,
        desde=desde, hasta=hasta
    )
    
    # Obtener total para paginación
    # (Deberia ser una consulta separada de count)
    total = len(await get_movimientos(db)) if not any([equipo_id, usuario_id, tipo_movimiento, estado, desde, hasta]) else len(movimientos)
    
    return PaginatedResponse.create(
        items=movimientos,
        total=total,
        page=(skip // limit) + 1,
        size=limit
    )


@router.post("/", response_model=ItemCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_movimiento_route(
    db: DbSession,
    current_user: MovimientosUser,
    movimiento_in: MovimientoCreate = Body(...)
) -> Any:
    """
    Crea un nuevo movimiento de equipo.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        movimiento_in: Datos del movimiento a crear
    """
    movimiento = await create_movimiento(db, movimiento_in, current_user["id"])
    
    return ItemCreatedResponse(
        id=movimiento["id"],
        message="Movimiento registrado correctamente"
    )


@router.get("/{movimiento_id}", response_model=ItemResponse[MovimientoConDetalles])
async def get_movimiento_by_id(
    db: DbSession,
    current_user: MovimientosUser,
    movimiento_id: uuid.UUID = Path(...)
) -> Any:
    """
    Obtiene un movimiento por su ID.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        movimiento_id: ID del movimiento
    """
    movimiento = await get_movimiento(db, movimiento_id)
    
    if not movimiento:
        raise NotFoundError("Movimiento no encontrado")
    
    return ItemResponse(data=movimiento)


@router.put("/{movimiento_id}", response_model=ItemUpdatedResponse)
async def update_movimiento_route(
    db: DbSession,
    current_user: MovimientosUser,
    movimiento_id: uuid.UUID = Path(...),
    movimiento_in: MovimientoUpdate = Body(...)
) -> Any:
    """
    Actualiza un movimiento existente.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        movimiento_id: ID del movimiento a actualizar
        movimiento_in: Datos actualizados del movimiento
    """
    movimiento = await get_movimiento(db, movimiento_id)
    
    if not movimiento:
        raise NotFoundError("Movimiento no encontrado")
    
    # Verificar que el movimiento no esté completado o cancelado
    if movimiento["estado"] in ["completado", "cancelado"]:
        raise BadRequestError("No se puede modificar un movimiento completado o cancelado")
    
    movimiento_actualizado = await update_movimiento(db, movimiento_id, movimiento_in)
    
    return ItemUpdatedResponse(
        id=movimiento_id,
        message="Movimiento actualizado correctamente"
    )


@router.post("/{movimiento_id}/autorizar", response_model=ItemUpdatedResponse)
async def autorizar_movimiento_route(
    db: DbSession,
    current_user: MovimientosAuthUser,
    movimiento_id: uuid.UUID = Path(...),
    autorizacion: MovimientoAutorizar = Body(...)
) -> Any:
    """
    Autoriza o rechaza un movimiento.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        movimiento_id: ID del movimiento a autorizar
        autorizacion: Datos de autorización
    """
    movimiento = await get_movimiento(db, movimiento_id)
    
    if not movimiento:
        raise NotFoundError("Movimiento no encontrado")
    
    # Verificar que el movimiento esté pendiente
    if movimiento["estado"] != "pendiente":
        raise BadRequestError("Solo se pueden autorizar movimientos pendientes")
    
    movimiento_actualizado = await autorizar_movimiento(
        db, movimiento_id, autorizacion.autorizado, 
        current_user["id"], autorizacion.observaciones
    )
    
    accion = "autorizado" if autorizacion.autorizado else "rechazado"
    
    return ItemUpdatedResponse(
        id=movimiento_id,
        message=f"Movimiento {accion} correctamente"
    )


@router.post("/{movimiento_id}/retorno", response_model=ItemUpdatedResponse)
async def registrar_retorno_route(
    db: DbSession,
    current_user: MovimientosUser,
    movimiento_id: uuid.UUID = Path(...),
    retorno: MovimientoRetorno = Body(...)
) -> Any:
    """
    Registra el retorno de un equipo.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        movimiento_id: ID del movimiento
        retorno: Datos de retorno
    """
    movimiento = await get_movimiento(db, movimiento_id)
    
    if not movimiento:
        raise NotFoundError("Movimiento no encontrado")
    
    # Verificar que el movimiento sea de tipo salida y esté en proceso
    if movimiento["tipo_movimiento"] != "salida":
        raise BadRequestError("Solo se puede registrar el retorno de movimientos de salida")
    
    if movimiento["estado"] != "en_proceso":
        raise BadRequestError("Solo se puede registrar el retorno de movimientos en proceso")
    
    movimiento_actualizado = await registrar_retorno(
        db, movimiento_id, retorno.recibido_por, retorno.observaciones
    )
    
    return ItemUpdatedResponse(
        id=movimiento_id,
        message="Retorno registrado correctamente"
    )


@router.post("/{movimiento_id}/cancelar", response_model=ItemUpdatedResponse)
async def cancelar_movimiento_route(
    db: DbSession,
    current_user: MovimientosUser,
    movimiento_id: uuid.UUID = Path(...),
    cancelacion: MovimientoCancelar = Body(...)
) -> Any:
    """
    Cancela un movimiento.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        movimiento_id: ID del movimiento a cancelar
        cancelacion: Datos de cancelación
    """
    movimiento = await get_movimiento(db, movimiento_id)
    
    if not movimiento:
        raise NotFoundError("Movimiento no encontrado")
    
    # Verificar que el movimiento no esté completado o cancelado
    if movimiento["estado"] in ["completado", "cancelado"]:
        raise BadRequestError("No se puede cancelar un movimiento completado o cancelado")
    
    movimiento_actualizado = await cancelar_movimiento(
        db, movimiento_id, cancelacion.motivo
    )
    
    return ItemUpdatedResponse(
        id=movimiento_id,
        message="Movimiento cancelado correctamente"
    )


@router.get("/reportes/vencidos", response_model=ItemsResponse[MovimientoConDetalles])
async def get_movimientos_vencidos_route(
    db: DbSession,
    current_user: MovimientosUser
) -> Any:
    """
    Obtiene los movimientos vencidos (fecha prevista de retorno superada).
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
    """
    movimientos = await get_movimientos_vencidos(db)
    
    return ItemsResponse(data=movimientos)
