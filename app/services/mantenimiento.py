from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.error_handlers import BadRequestError, NotFoundError
from app.db.models.equipos import Equipo
from app.db.models.mantenimiento import Mantenimiento, TipoMantenimiento
from app.schemas.mantenimiento import (
    MantenimientoCreate, MantenimientoUpdate, 
    TipoMantenimientoCreate, TipoMantenimientoUpdate
)


# Servicios para Tipos de Mantenimiento
async def get_tipos_mantenimiento(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Obtiene todos los tipos de mantenimiento.
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        Lista de tipos de mantenimiento
    """
    stmt = select(TipoMantenimiento)
    result = await db.execute(stmt)
    tipos = result.scalars().all()
    
    return [tipo.to_dict() for tipo in tipos]


async def get_tipo_mantenimiento(
    db: AsyncSession, 
    tipo_id: uuid.UUID
) -> Optional[Dict[str, Any]]:
    """
    Obtiene un tipo de mantenimiento por su ID.
    
    Args:
        db: Sesión de base de datos
        tipo_id: ID del tipo de mantenimiento
        
    Returns:
        Tipo de mantenimiento encontrado o None
    """
    stmt = select(TipoMantenimiento).where(TipoMantenimiento.id == tipo_id)
    result = await db.execute(stmt)
    tipo = result.scalar_one_or_none()
    
    return tipo.to_dict() if tipo else None


async def create_tipo_mantenimiento(
    db: AsyncSession, 
    data: TipoMantenimientoCreate
) -> Dict[str, Any]:
    """
    Crea un nuevo tipo de mantenimiento.
    
    Args:
        db: Sesión de base de datos
        data: Datos del tipo de mantenimiento a crear
        
    Returns:
        Tipo de mantenimiento creado
    """
    tipo = TipoMantenimiento(**data.model_dump())
    db.add(tipo)
    await db.commit()
    await db.refresh(tipo)
    
    return tipo.to_dict()


async def update_tipo_mantenimiento(
    db: AsyncSession, 
    tipo_id: uuid.UUID, 
    data: TipoMantenimientoUpdate
) -> Optional[Dict[str, Any]]:
    """
    Actualiza un tipo de mantenimiento existente.
    
    Args:
        db: Sesión de base de datos
        tipo_id: ID del tipo de mantenimiento a actualizar
        data: Datos actualizados del tipo de mantenimiento
        
    Returns:
        Tipo de mantenimiento actualizado o None si no existe
    """
    stmt = select(TipoMantenimiento).where(TipoMantenimiento.id == tipo_id)
    result = await db.execute(stmt)
    tipo = result.scalar_one_or_none()
    
    if not tipo:
        return None
    
    update_data = data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if hasattr(tipo, field):
            setattr(tipo, field, value)
    
    await db.commit()
    await db.refresh(tipo)
    
    return tipo.to_dict()


async def delete_tipo_mantenimiento(
    db: AsyncSession, 
    tipo_id: uuid.UUID
) -> bool:
    """
    Elimina un tipo de mantenimiento.
    
    Args:
        db: Sesión de base de datos
        tipo_id: ID del tipo de mantenimiento a eliminar
        
    Returns:
        True si se eliminó correctamente, False en caso contrario
    """
    # Verificar si hay mantenimientos asociados
    stmt = select(Mantenimiento).where(Mantenimiento.tipo_mantenimiento_id == tipo_id).limit(1)
    result = await db.execute(stmt)
    existe_mantenimiento = result.scalar_one_or_none() is not None
    
    if existe_mantenimiento:
        raise BadRequestError("No se puede eliminar el tipo de mantenimiento porque existen mantenimientos asociados")
    
    # Eliminar tipo de mantenimiento
    stmt = select(TipoMantenimiento).where(TipoMantenimiento.id == tipo_id)
    result = await db.execute(stmt)
    tipo = result.scalar_one_or_none()
    
    if not tipo:
        return False
    
    await db.delete(tipo)
    await db.commit()
    
    return True


# Servicios para Mantenimientos
async def get_mantenimiento(
    db: AsyncSession, 
    mantenimiento_id: uuid.UUID
) -> Optional[Dict[str, Any]]:
    """
    Obtiene un mantenimiento por su ID.
    
    Args:
        db: Sesión de base de datos
        mantenimiento_id: ID del mantenimiento
        
    Returns:
        Mantenimiento encontrado o None
    """
    stmt = select(Mantenimiento).where(Mantenimiento.id == mantenimiento_id).options(
        joinedload(Mantenimiento.equipo),
        joinedload(Mantenimiento.tipo_mantenimiento)
    )
    result = await db.execute(stmt)
    mantenimiento = result.unique().scalar_one_or_none()
    
    if not mantenimiento:
        return None
        
    mant_dict = mantenimiento.to_dict()
    
    # Agregar relaciones
    if mantenimiento.equipo:
        mant_dict["equipo"] = {
            "id": mantenimiento.equipo.id,
            "nombre": mantenimiento.equipo.nombre,
            "numero_serie": mantenimiento.equipo.numero_serie
        }
        # Añadir campos planos requeridos por el esquema
        mant_dict["equipo_nombre"] = mantenimiento.equipo.nombre
        mant_dict["equipo_numero_serie"] = mantenimiento.equipo.numero_serie
        
    if mantenimiento.tipo_mantenimiento:
        mant_dict["tipo_mantenimiento"] = {
            "id": mantenimiento.tipo_mantenimiento.id,
            "nombre": mantenimiento.tipo_mantenimiento.nombre,
            "periodicidad_dias": mantenimiento.tipo_mantenimiento.periodicidad_dias
        }
        # Añadir campo plano requerido por el esquema
        mant_dict["tipo_mantenimiento_nombre"] = mantenimiento.tipo_mantenimiento.nombre
        
    # Calcular información adicional
    mant_dict["vencido"] = False
    if mantenimiento.estado in ["programado", "en_proceso"] and mantenimiento.fecha_mantenimiento < datetime.now(timezone.utc):
        mant_dict["vencido"] = True
        
    if mantenimiento.fecha_proximo_mantenimiento:
        dias = (mantenimiento.fecha_proximo_mantenimiento - datetime.now(timezone.utc)).days
        mant_dict["dias_para_proximo"] = max(0, dias)
            
    return mant_dict


async def get_mantenimientos(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    equipo_id: Optional[uuid.UUID] = None,
    tipo_id: Optional[uuid.UUID] = None,
    estado: Optional[str] = None,
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None,
    vencidos: Optional[bool] = None
) -> List[Dict[str, Any]]:
    """
    Obtiene una lista de mantenimientos con filtros opcionales.
    
    Args:
        db: Sesión de base de datos
        skip: Número de registros a omitir (paginación)
        limit: Límite de registros a devolver
        equipo_id: Filtrar por ID de equipo
        tipo_id: Filtrar por ID de tipo de mantenimiento
        estado: Filtrar por estado
        desde: Filtrar por fecha desde
        hasta: Filtrar por fecha hasta
        vencidos: Filtrar solo vencidos
        
    Returns:
        Lista de mantenimientos
    """
    # Construir consulta base
    query = select(Mantenimiento).options(
        joinedload(Mantenimiento.equipo),
        joinedload(Mantenimiento.tipo_mantenimiento)
    )
    
    # Aplicar filtros
    if equipo_id:
        query = query.where(Mantenimiento.equipo_id == equipo_id)
    
    if tipo_id:
        query = query.where(Mantenimiento.tipo_mantenimiento_id == tipo_id)
    
    if estado:
        query = query.where(Mantenimiento.estado == estado)
        
    if desde:
        query = query.where(Mantenimiento.fecha_mantenimiento >= desde)
        
    if hasta:
        query = query.where(Mantenimiento.fecha_mantenimiento <= hasta)
        
    if vencidos:
        query = query.where(
            and_(
                Mantenimiento.estado.in_(["programado", "en_proceso"]),
                Mantenimiento.fecha_mantenimiento < datetime.now(timezone.utc)
            )
        )
    
    # Ordenar por fecha (más recientes primero)
    query = query.order_by(Mantenimiento.fecha_mantenimiento.desc())
    
    # Aplicar paginación
    query = query.offset(skip).limit(limit)
    
    # Ejecutar consulta
    result = await db.execute(query)
    mantenimientos = result.unique().scalars().all()
    
    # Convertir a lista de diccionarios con información adicional
    mantenimientos_list = []
    for mant in mantenimientos:
        mant_dict = mant.to_dict()
        
        # Agregar relaciones
        if mant.equipo:
            mant_dict["equipo"] = {
                "id": mant.equipo.id,
                "nombre": mant.equipo.nombre,
                "numero_serie": mant.equipo.numero_serie
            }
            # Añadir campos planos requeridos por el esquema
            mant_dict["equipo_nombre"] = mant.equipo.nombre
            mant_dict["equipo_numero_serie"] = mant.equipo.numero_serie
            
        if mant.tipo_mantenimiento:
            mant_dict["tipo_mantenimiento"] = {
                "id": mant.tipo_mantenimiento.id,
                "nombre": mant.tipo_mantenimiento.nombre,
                "periodicidad_dias": mant.tipo_mantenimiento.periodicidad_dias
            }
            # Añadir campo plano requerido por el esquema
            mant_dict["tipo_mantenimiento_nombre"] = mant.tipo_mantenimiento.nombre
            
        # Calcular información adicional
        mant_dict["vencido"] = False
        if mant.estado in ["programado", "en_proceso"] and mant.fecha_mantenimiento < datetime.now(timezone.utc):
            mant_dict["vencido"] = True
            
        if mant.fecha_proximo_mantenimiento:
            dias = (mant.fecha_proximo_mantenimiento - datetime.now(timezone.utc)).days
            mant_dict["dias_para_proximo"] = max(0, dias)
                
        mantenimientos_list.append(mant_dict)
        
    return mantenimientos_list


async def create_mantenimiento(
    db: AsyncSession, 
    data: MantenimientoCreate
) -> Dict[str, Any]:
    """
    Crea un nuevo mantenimiento.
    
    Args:
        db: Sesión de base de datos
        data: Datos del mantenimiento a crear
        
    Returns:
        Mantenimiento creado
    """
    # Verificar que el equipo existe
    stmt = select(Equipo).where(Equipo.id == data.equipo_id)
    result = await db.execute(stmt)
    equipo = result.scalar_one_or_none()
    
    if not equipo:
        raise NotFoundError("Equipo no encontrado")
        
    # Verificar que el tipo de mantenimiento existe
    stmt = select(TipoMantenimiento).where(TipoMantenimiento.id == data.tipo_mantenimiento_id)
    result = await db.execute(stmt)
    tipo = result.scalar_one_or_none()
    
    if not tipo:
        raise NotFoundError("Tipo de mantenimiento no encontrado")
    
    # Fecha de mantenimiento (por defecto la actual si no se proporciona)
    fecha_mantenimiento = data.fecha_mantenimiento if data.fecha_mantenimiento else datetime.now(timezone.utc)
    
    # Crear objeto de mantenimiento
    mantenimiento = Mantenimiento(
        equipo_id=data.equipo_id,
        tipo_mantenimiento_id=data.tipo_mantenimiento_id,
        fecha_mantenimiento=fecha_mantenimiento,
        tecnico_responsable=data.tecnico_responsable,
        costo=data.costo,
        observaciones=data.observaciones,
        estado="programado"
    )
    
    # Calcular fecha del próximo mantenimiento si el tipo tiene periodicidad
    if tipo.periodicidad_dias:
        mantenimiento.fecha_proximo_mantenimiento = fecha_mantenimiento + timedelta(days=tipo.periodicidad_dias)
    
    db.add(mantenimiento)
    await db.commit()
    await db.refresh(mantenimiento)
    
    # Obtener el mantenimiento con sus relaciones
    return await get_mantenimiento(db, mantenimiento.id)


async def update_mantenimiento(
    db: AsyncSession, 
    mantenimiento_id: uuid.UUID, 
    data: Union[MantenimientoUpdate, Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Actualiza un mantenimiento existente.
    
    Args:
        db: Sesión de base de datos
        mantenimiento_id: ID del mantenimiento a actualizar
        data: Datos actualizados del mantenimiento
        
    Returns:
        Mantenimiento actualizado o None si no existe
    """
    # Obtener mantenimiento existente
    stmt = select(Mantenimiento).where(Mantenimiento.id == mantenimiento_id).options(
        joinedload(Mantenimiento.tipo_mantenimiento)
    )
    result = await db.execute(stmt)
    mantenimiento = result.unique().scalar_one_or_none()
    
    if not mantenimiento:
        return None
    
    # Convertir a diccionario si es un modelo Pydantic
    update_data = data if isinstance(data, dict) else data.model_dump(exclude_unset=True)
    
    # Validar estado
    if "estado" in update_data and update_data["estado"] not in ["programado", "en_proceso", "completado", "cancelado"]:
        raise BadRequestError("Estado inválido")
    
    # Si se cambia el tipo de mantenimiento, verificar que existe
    if "tipo_mantenimiento_id" in update_data and update_data["tipo_mantenimiento_id"] != mantenimiento.tipo_mantenimiento_id:
        stmt = select(TipoMantenimiento).where(TipoMantenimiento.id == update_data["tipo_mantenimiento_id"])
        result = await db.execute(stmt)
        tipo = result.scalar_one_or_none()
        
        if not tipo:
            raise NotFoundError("Tipo de mantenimiento no encontrado")
            
        # Actualizar fecha del próximo mantenimiento si el tipo tiene periodicidad
        if tipo.periodicidad_dias:
            fecha_base = mantenimiento.fecha_mantenimiento
            update_data["fecha_proximo_mantenimiento"] = fecha_base + timedelta(days=tipo.periodicidad_dias)
    
    # Si cambia a completado, actualizar la fecha del próximo mantenimiento
    if (
        "estado" in update_data and 
        update_data["estado"] == "completado" and 
        mantenimiento.estado != "completado" and
        mantenimiento.tipo_mantenimiento and 
        mantenimiento.tipo_mantenimiento.periodicidad_dias
    ):
        fecha_base = update_data.get("fecha_mantenimiento", mantenimiento.fecha_mantenimiento)
        update_data["fecha_proximo_mantenimiento"] = fecha_base + timedelta(
            days=mantenimiento.tipo_mantenimiento.periodicidad_dias
        )
    
    # Actualizar mantenimiento
    for field, value in update_data.items():
        if hasattr(mantenimiento, field):
            setattr(mantenimiento, field, value)
    
    await db.commit()
    await db.refresh(mantenimiento)
    
    # Obtener el mantenimiento actualizado con sus relaciones
    return await get_mantenimiento(db, mantenimiento_id)


async def cambiar_estado_mantenimiento(
    db: AsyncSession, 
    mantenimiento_id: uuid.UUID, 
    nuevo_estado: str,
    observaciones: Optional[str] = None,
    costo: Optional[Decimal] = None
) -> Optional[Dict[str, Any]]:
    """
    Cambia el estado de un mantenimiento.
    
    Args:
        db: Sesión de base de datos
        mantenimiento_id: ID del mantenimiento
        nuevo_estado: Nuevo estado
        observaciones: Observaciones opcionales
        costo: Costo del mantenimiento (para estado completado)
        
    Returns:
        Mantenimiento actualizado o None si no existe
    """
    # Validar estado
    if nuevo_estado not in ["programado", "en_proceso", "completado", "cancelado"]:
        raise BadRequestError("Estado inválido")
    
    # Obtener mantenimiento
    stmt = select(Mantenimiento).where(Mantenimiento.id == mantenimiento_id).options(
        joinedload(Mantenimiento.tipo_mantenimiento)
    )
    result = await db.execute(stmt)
    mantenimiento = result.unique().scalar_one_or_none()
    
    if not mantenimiento:
        return None
    
    # Validar transición de estado
    if nuevo_estado == mantenimiento.estado:
        return await get_mantenimiento(db, mantenimiento_id)
    
    # Actualizar estado
    mantenimiento.estado = nuevo_estado
    
    # Actualizar observaciones si se proporcionan
    if observaciones:
        mantenimiento.observaciones = observaciones
    
    # Actualizar costo si se proporciona y el estado es completado
    if costo is not None and nuevo_estado == "completado":
        mantenimiento.costo = costo
    
    # Si cambia a completado, actualizar la fecha del próximo mantenimiento
    if (
        nuevo_estado == "completado" and 
        mantenimiento.tipo_mantenimiento and 
        mantenimiento.tipo_mantenimiento.periodicidad_dias
    ):
        mantenimiento.fecha_proximo_mantenimiento = mantenimiento.fecha_mantenimiento + timedelta(
            days=mantenimiento.tipo_mantenimiento.periodicidad_dias
        )
    
    await db.commit()
    await db.refresh(mantenimiento)
    
    return await get_mantenimiento(db, mantenimiento_id)


async def delete_mantenimiento(
    db: AsyncSession, 
    mantenimiento_id: uuid.UUID
) -> bool:
    """
    Elimina un mantenimiento.
    
    Args:
        db: Sesión de base de datos
        mantenimiento_id: ID del mantenimiento a eliminar
        
    Returns:
        True si se eliminó correctamente, False en caso contrario
    """
    stmt = select(Mantenimiento).where(Mantenimiento.id == mantenimiento_id)
    result = await db.execute(stmt)
    mantenimiento = result.scalar_one_or_none()
    
    if not mantenimiento:
        return False
    
    await db.delete(mantenimiento)
    await db.commit()
    
    return True


async def get_proximos_mantenimientos(
    db: AsyncSession, 
    dias: int = 30
) -> List[Dict[str, Any]]:
    """
    Obtiene los mantenimientos programados para los próximos días.
    
    Args:
        db: Sesión de base de datos
        dias: Número de días a considerar
        
    Returns:
        Lista de mantenimientos programados
    """
    fecha_limite = datetime.now(timezone.utc) + timedelta(days=dias)
    
    stmt = select(Mantenimiento).where(
        and_(
            Mantenimiento.estado.in_(["programado"]),
            Mantenimiento.fecha_mantenimiento <= fecha_limite,
            Mantenimiento.fecha_mantenimiento >= datetime.now(timezone.utc)
        )
    ).options(
        joinedload(Mantenimiento.equipo),
        joinedload(Mantenimiento.tipo_mantenimiento)
    ).order_by(Mantenimiento.fecha_mantenimiento)
    
    result = await db.execute(stmt)
    mantenimientos = result.unique().scalars().all()
    
    # Convertir a lista de diccionarios con información adicional
    mantenimientos_list = []
    for mant in mantenimientos:
        mant_dict = mant.to_dict()
        
        # Agregar relaciones
        if mant.equipo:
            mant_dict["equipo"] = {
                "id": mant.equipo.id,
                "nombre": mant.equipo.nombre,
                "numero_serie": mant.equipo.numero_serie
            }
            # Añadir campos planos requeridos por el esquema
            mant_dict["equipo_nombre"] = mant.equipo.nombre
            mant_dict["equipo_numero_serie"] = mant.equipo.numero_serie
            
        if mant.tipo_mantenimiento:
            mant_dict["tipo_mantenimiento"] = {
                "id": mant.tipo_mantenimiento.id,
                "nombre": mant.tipo_mantenimiento.nombre
            }
            # Añadir campo plano requerido por el esquema
            mant_dict["tipo_mantenimiento_nombre"] = mant.tipo_mantenimiento.nombre
            
        # Calcular días restantes
        dias_restantes = (mant.fecha_mantenimiento - datetime.now(timezone.utc)).days
        mant_dict["dias_restantes"] = max(0, dias_restantes)
                
        mantenimientos_list.append(mant_dict)
        
    return mantenimientos_list
