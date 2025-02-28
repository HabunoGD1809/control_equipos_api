from datetime import datetime
import uuid
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.error_handlers import BadRequestError, NotFoundError
from app.db.models.equipos import Equipo
from app.db.models.movimientos import Movimiento
from app.db.models.usuarios import Usuario
from app.schemas.movimientos import MovimientoCreate, MovimientoUpdate


async def get_movimiento(db: AsyncSession, movimiento_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    """
    Obtiene un movimiento por su ID.
    
    Args:
        db: Sesión de base de datos
        movimiento_id: ID del movimiento
        
    Returns:
        Movimiento encontrado o None
    """
    stmt = select(Movimiento).where(Movimiento.id == movimiento_id).options(
        joinedload(Movimiento.equipo),
        joinedload(Movimiento.usuario),
        joinedload(Movimiento.autorizado_por_usuario)
    )
    result = await db.execute(stmt)
    movimiento = result.unique().scalar_one_or_none()
    
    if not movimiento:
        return None
        
    mov_dict = movimiento.to_dict()
    
    # Agregar información adicional
    if movimiento.equipo:
        mov_dict["equipo"] = {
            "id": movimiento.equipo.id,
            "nombre": movimiento.equipo.nombre,
            "numero_serie": movimiento.equipo.numero_serie
        }
        
    if movimiento.usuario:
        mov_dict["usuario"] = {
            "id": movimiento.usuario.id,
            "nombre_usuario": movimiento.usuario.nombre_usuario
        }
        
    if movimiento.autorizado_por_usuario:
        mov_dict["autorizado_por_usuario"] = {
            "id": movimiento.autorizado_por_usuario.id,
            "nombre_usuario": movimiento.autorizado_por_usuario.nombre_usuario
        }
        
    # Calcular si está retrasado y días restantes
    if movimiento.tipo_movimiento == "salida" and movimiento.fecha_prevista_retorno and not movimiento.fecha_retorno:
        if datetime.now(timezone.utc) > movimiento.fecha_prevista_retorno:
            mov_dict["retrasado"] = True
        else:
            mov_dict["retrasado"] = False
            dias = (movimiento.fecha_prevista_retorno - datetime.now(timezone.utc)).days
            mov_dict["dias_restantes"] = max(0, dias)
            
    return mov_dict


async def get_movimientos(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    equipo_id: Optional[uuid.UUID] = None,
    usuario_id: Optional[uuid.UUID] = None,
    tipo_movimiento: Optional[str] = None,
    estado: Optional[str] = None,
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Obtiene una lista de movimientos con filtros opcionales.
    
    Args:
        db: Sesión de base de datos
        skip: Número de registros a omitir (paginación)
        limit: Límite de registros a devolver
        equipo_id: Filtrar por ID de equipo
        usuario_id: Filtrar por ID de usuario
        tipo_movimiento: Filtrar por tipo de movimiento
        estado: Filtrar por estado
        desde: Filtrar por fecha desde
        hasta: Filtrar por fecha hasta
        
    Returns:
        Lista de movimientos
    """
    # Construir consulta base
    query = select(Movimiento).options(
        joinedload(Movimiento.equipo),
        joinedload(Movimiento.usuario),
        joinedload(Movimiento.autorizado_por_usuario)
    )
    
    # Aplicar filtros
    if equipo_id:
        query = query.where(Movimiento.equipo_id == equipo_id)
    
    if usuario_id:
        query = query.where(Movimiento.usuario_id == usuario_id)
    
    if tipo_movimiento:
        query = query.where(Movimiento.tipo_movimiento == tipo_movimiento)
        
    if estado:
        query = query.where(Movimiento.estado == estado)
        
    if desde:
        query = query.where(Movimiento.fecha_hora >= desde)
        
    if hasta:
        query = query.where(Movimiento.fecha_hora <= hasta)
    
    # Ordenar por fecha (más recientes primero)
    query = query.order_by(Movimiento.fecha_hora.desc())
    
    # Aplicar paginación
    query = query.offset(skip).limit(limit)
    
    # Ejecutar consulta
    result = await db.execute(query)
    movimientos = result.unique().scalars().all()
    
    # Convertir a lista de diccionarios con información adicional
    movimientos_list = []
    for mov in movimientos:
        mov_dict = mov.to_dict()
        
        # Agregar información adicional
        if mov.equipo:
            mov_dict["equipo"] = {
                "id": mov.equipo.id,
                "nombre": mov.equipo.nombre,
                "numero_serie": mov.equipo.numero_serie
            }
            
        if mov.usuario:
            mov_dict["usuario"] = {
                "id": mov.usuario.id,
                "nombre_usuario": mov.usuario.nombre_usuario
            }
            
        if mov.autorizado_por_usuario:
            mov_dict["autorizado_por_usuario"] = {
                "id": mov.autorizado_por_usuario.id,
                "nombre_usuario": mov.autorizado_por_usuario.nombre_usuario
            }
            
        # Calcular si está retrasado y días restantes
        if mov.tipo_movimiento == "salida" and mov.fecha_prevista_retorno and not mov.fecha_retorno:
            if datetime.now(timezone.utc) > mov.fecha_prevista_retorno:
                mov_dict["retrasado"] = True
            else:
                mov_dict["retrasado"] = False
                dias = (mov.fecha_prevista_retorno - datetime.now(timezone.utc)).days
                mov_dict["dias_restantes"] = max(0, dias)
                
        movimientos_list.append(mov_dict)
        
    return movimientos_list


async def create_movimiento(
    db: AsyncSession, 
    movimiento_in: MovimientoCreate, 
    usuario_id: uuid.UUID
) -> Dict[str, Any]:
    """
    Crea un nuevo movimiento de equipo.
    
    Args:
        db: Sesión de base de datos
        movimiento_in: Datos del movimiento a crear
        usuario_id: ID del usuario que registra el movimiento
        
    Returns:
        Movimiento creado
    """
    # Verificar que el equipo existe y está disponible para movimientos
    stmt = select(Equipo).where(Equipo.id == movimiento_in.equipo_id).options(
        joinedload(Equipo.estado)
    )
    result = await db.execute(stmt)
    equipo = result.unique().scalar_one_or_none()
    
    if not equipo:
        raise NotFoundError("Equipo no encontrado")
        
    if not equipo.estado or not equipo.estado.permite_movimientos:
        raise BadRequestError("El equipo no está disponible para movimientos")
        
    # Crear objeto de movimiento
    db_movimiento = Movimiento(
        **movimiento_in.model_dump(),
        usuario_id=usuario_id,
        estado="pendiente"
    )
    
    # Si el equipo no requiere autorización, establecer estado como en_proceso
    if not equipo.estado.requiere_autorizacion:
        db_movimiento.estado = "en_proceso"
    
    # Guardar en la base de datos
    db.add(db_movimiento)
    await db.commit()
    await db.refresh(db_movimiento)
    
    # Actualizar estado y ubicación del equipo si el movimiento es de tipo salida
    # y no requiere autorización o está autorizado
    if db_movimiento.tipo_movimiento == "salida" and db_movimiento.estado == "en_proceso":
        equipo.estado_id = await get_estado_equipo_by_nombre(db, "prestado")
        if db_movimiento.destino:
            equipo.ubicacion_actual = db_movimiento.destino
        await db.commit()
        
    # Obtener el movimiento con sus relaciones
    return await get_movimiento(db, db_movimiento.id)


async def update_movimiento(
    db: AsyncSession, 
    movimiento_id: uuid.UUID, 
    movimiento_in: Union[MovimientoUpdate, Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Actualiza un movimiento existente.
    
    Args:
        db: Sesión de base de datos
        movimiento_id: ID del movimiento a actualizar
        movimiento_in: Datos actualizados del movimiento
        
    Returns:
        Movimiento actualizado o None si no existe
    """
    # Obtener movimiento existente
    stmt = select(Movimiento).where(Movimiento.id == movimiento_id)
    result = await db.execute(stmt)
    db_movimiento = result.scalar_one_or_none()
    
    if not db_movimiento:
        return None
    
    # Convertir a diccionario si es un modelo Pydantic
    update_data = movimiento_in if isinstance(movimiento_in, dict) else movimiento_in.model_dump(exclude_unset=True)
    
    # Validar estado
    if "estado" in update_data and update_data["estado"] not in ["pendiente", "en_proceso", "completado", "cancelado"]:
        raise BadRequestError("Estado inválido")
    
    # Actualizar movimiento
    for field, value in update_data.items():
        if hasattr(db_movimiento, field):
            setattr(db_movimiento, field, value)
    
    await db.commit()
    await db.refresh(db_movimiento)
    
    # Obtener el movimiento actualizado con sus relaciones
    return await get_movimiento(db, db_movimiento.id)


async def autorizar_movimiento(
    db: AsyncSession, 
    movimiento_id: uuid.UUID, 
    autorizar: bool, 
    autorizador_id: uuid.UUID,
    observaciones: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Autoriza o rechaza un movimiento.
    
    Args:
        db: Sesión de base de datos
        movimiento_id: ID del movimiento a autorizar
        autorizar: True para autorizar, False para rechazar
        autorizador_id: ID del usuario que autoriza
        observaciones: Observaciones opcionales
        
    Returns:
        Movimiento actualizado o None si no existe
    """
    # Obtener movimiento
    stmt = select(Movimiento).where(
        and_(Movimiento.id == movimiento_id, Movimiento.estado == "pendiente")
    ).options(
        joinedload(Movimiento.equipo)
    )
    result = await db.execute(stmt)
    movimiento = result.unique().scalar_one_or_none()
    
    if not movimiento:
        return None
    
    # Actualizar movimiento
    movimiento.autorizado_por = autorizador_id
    
    if autorizar:
        movimiento.estado = "en_proceso"
        
        # Actualizar estado y ubicación del equipo si es una salida
        if movimiento.tipo_movimiento == "salida" and movimiento.equipo:
            movimiento.equipo.estado_id = await get_estado_equipo_by_nombre(db, "prestado")
            if movimiento.destino:
                movimiento.equipo.ubicacion_actual = movimiento.destino
    else:
        movimiento.estado = "cancelado"
        
    if observaciones:
        movimiento.observaciones = observaciones
    
    await db.commit()
    await db.refresh(movimiento)
    
    return await get_movimiento(db, movimiento_id)


async def registrar_retorno(
    db: AsyncSession, 
    movimiento_id: uuid.UUID, 
    recibido_por: str,
    observaciones: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Registra el retorno de un equipo.
    
    Args:
        db: Sesión de base de datos
        movimiento_id: ID del movimiento
        recibido_por: Nombre de quien recibe el equipo
        observaciones: Observaciones opcionales
        
    Returns:
        Movimiento actualizado o None si no existe
    """
    # Obtener movimiento
    stmt = select(Movimiento).where(
        and_(
            Movimiento.id == movimiento_id,
            Movimiento.tipo_movimiento == "salida",
            Movimiento.estado == "en_proceso"
        )
    ).options(
        joinedload(Movimiento.equipo)
    )
    result = await db.execute(stmt)
    movimiento = result.unique().scalar_one_or_none()
    
    if not movimiento:
        return None
    
    # Actualizar movimiento
    movimiento.fecha_retorno = datetime.now(timezone.utc)
    movimiento.recibido_por = recibido_por
    movimiento.estado = "completado"
    
    if observaciones:
        movimiento.observaciones = observaciones
    
    # Actualizar estado del equipo
    if movimiento.equipo:
        movimiento.equipo.estado_id = await get_estado_equipo_by_nombre(db, "disponible")
        movimiento.equipo.ubicacion_actual = "Almacén principal"  # Valor por defecto
    
    await db.commit()
    await db.refresh(movimiento)
    
    return await get_movimiento(db, movimiento_id)


async def cancelar_movimiento(
    db: AsyncSession, 
    movimiento_id: uuid.UUID, 
    motivo: str
) -> Optional[Dict[str, Any]]:
    """
    Cancela un movimiento.
    
    Args:
        db: Sesión de base de datos
        movimiento_id: ID del movimiento a cancelar
        motivo: Motivo de la cancelación
        
    Returns:
        Movimiento actualizado o None si no existe
    """
    # Obtener movimiento
    stmt = select(Movimiento).where(
        and_(
            Movimiento.id == movimiento_id,
            Movimiento.estado.in_(["pendiente", "en_proceso"])
        )
    ).options(
        joinedload(Movimiento.equipo)
    )
    result = await db.execute(stmt)
    movimiento = result.unique().scalar_one_or_none()
    
    if not movimiento:
        return None
    
    # Actualizar movimiento
    movimiento.estado = "cancelado"
    movimiento.observaciones = f"Cancelado: {motivo}"
    
    # Si el movimiento estaba en proceso (ya había salido), devolver el equipo
    if movimiento.estado == "en_proceso" and movimiento.tipo_movimiento == "salida" and movimiento.equipo:
        movimiento.equipo.estado_id = await get_estado_equipo_by_nombre(db, "disponible")
        movimiento.equipo.ubicacion_actual = "Almacén principal"  # Valor por defecto
    
    await db.commit()
    await db.refresh(movimiento)
    
    return await get_movimiento(db, movimiento_id)


async def get_movimientos_vencidos(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Obtiene los movimientos vencidos (fecha prevista de retorno superada).
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        Lista de movimientos vencidos
    """
    stmt = select(Movimiento).where(
        and_(
            Movimiento.tipo_movimiento == "salida",
            Movimiento.estado == "en_proceso",
            Movimiento.fecha_prevista_retorno < datetime.now(timezone.utc),
            Movimiento.fecha_retorno.is_(None)
        )
    ).options(
        joinedload(Movimiento.equipo),
        joinedload(Movimiento.usuario)
    )
    
    result = await db.execute(stmt)
    movimientos = result.unique().scalars().all()
    
    # Convertir a lista de diccionarios con información adicional
    movimientos_list = []
    for mov in movimientos:
        mov_dict = mov.to_dict()
        
        # Agregar información adicional
        if mov.equipo:
            mov_dict["equipo"] = {
                "id": mov.equipo.id,
                "nombre": mov.equipo.nombre,
                "numero_serie": mov.equipo.numero_serie
            }
            
        if mov.usuario:
            mov_dict["usuario"] = {
                "id": mov.usuario.id,
                "nombre_usuario": mov.usuario.nombre_usuario
            }
            
        # Calcular días de retraso
        dias_retraso = (datetime.now(timezone.utc) - mov.fecha_prevista_retorno).days
        mov_dict["dias_retraso"] = max(0, dias_retraso)
                
        movimientos_list.append(mov_dict)
        
    return movimientos_list


# Funciones auxiliares
async def get_estado_equipo_by_nombre(db: AsyncSession, nombre: str) -> uuid.UUID:
    """
    Obtiene el ID de un estado de equipo por su nombre.
    
    Args:
        db: Sesión de base de datos
        nombre: Nombre del estado
        
    Returns:
        ID del estado
    """
    from app.db.models.equipos import EstadoEquipo
    
    stmt = select(EstadoEquipo.id).where(EstadoEquipo.nombre == nombre)
    result = await db.execute(stmt)
    estado_id = result.scalar_one_or_none()
    
    if not estado_id:
        raise NotFoundError(f"Estado de equipo '{nombre}' no encontrado")
        
    return estado_id
