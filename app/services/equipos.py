from datetime import date, datetime, timezone
import uuid
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models.equipos import (
    Documentacion, Equipo, EstadoEquipo, Proveedor, TipoDocumento
)
from app.schemas.equipos import (
    EquipoCreate, EquipoUpdate, ProveedorCreate, ProveedorUpdate,
    DocumentacionCreate, DocumentacionUpdate, DocumentacionVerificar
)


# Servicios para Equipos
async def get_equipo(db: AsyncSession, equipo_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    """
    Obtiene un equipo por su ID.
    
    Args:
        db: Sesión de base de datos
        equipo_id: ID del equipo
        
    Returns:
        Equipo encontrado o None
    """
    stmt = select(Equipo).where(Equipo.id == equipo_id).options(
        joinedload(Equipo.estado),
        joinedload(Equipo.proveedor)
    )
    result = await db.execute(stmt)
    equipo = result.unique().scalar_one_or_none()
    
    if not equipo:
        return None
        
    equipo_dict = equipo.to_dict()
    
    # Agregar relaciones
    if equipo.estado:
        equipo_dict["estado"] = equipo.estado.to_dict()
    if equipo.proveedor:
        equipo_dict["proveedor"] = equipo.proveedor.to_dict()
        
    return equipo_dict


async def get_equipos(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    estado_id: Optional[uuid.UUID] = None,
    proveedor_id: Optional[uuid.UUID] = None,
    search: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Obtiene una lista de equipos con filtros opcionales.
    
    Args:
        db: Sesión de base de datos
        skip: Número de registros a omitir (paginación)
        limit: Límite de registros a devolver
        estado_id: Filtrar por ID de estado
        proveedor_id: Filtrar por ID de proveedor
        search: Término de búsqueda
        
    Returns:
        Lista de equipos
    """
    # Construir consulta base
    query = select(Equipo).options(
        joinedload(Equipo.estado),
        joinedload(Equipo.proveedor)
    )
    
    # Aplicar filtros
    if estado_id:
        query = query.where(Equipo.estado_id == estado_id)
    
    if proveedor_id:
        query = query.where(Equipo.proveedor_id == proveedor_id)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (Equipo.nombre.ilike(search_term)) |
            (Equipo.numero_serie.ilike(search_term)) |
            (Equipo.marca.ilike(search_term)) |
            (Equipo.modelo.ilike(search_term)) |
            (Equipo.notas.ilike(search_term))
        )
    
    # Aplicar paginación
    query = query.offset(skip).limit(limit)
    
    # Ejecutar consulta
    result = await db.execute(query)
    equipos = result.unique().scalars().all()
    
    # Convertir a lista de diccionarios con relaciones
    equipos_list = []
    for equipo in equipos:
        equipo_dict = equipo.to_dict()
        
        if equipo.estado:
            equipo_dict["estado"] = equipo.estado.to_dict()
        if equipo.proveedor:
            equipo_dict["proveedor"] = equipo.proveedor.to_dict()
            
        equipos_list.append(equipo_dict)
        
    return equipos_list


async def create_equipo(db: AsyncSession, equipo_in: EquipoCreate) -> Dict[str, Any]:
    """
    Crea un nuevo equipo.
    
    Args:
        db: Sesión de base de datos
        equipo_in: Datos del equipo a crear
        
    Returns:
        Equipo creado
    """
    # Crear objeto de equipo
    db_equipo = Equipo(**equipo_in.model_dump())
    
    # Guardar en la base de datos
    db.add(db_equipo)
    await db.commit()
    await db.refresh(db_equipo)
    
    # Obtener el equipo con sus relaciones
    return await get_equipo(db, db_equipo.id)


async def update_equipo(
    db: AsyncSession, 
    equipo_id: uuid.UUID, 
    equipo_in: Union[EquipoUpdate, Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Actualiza un equipo existente.
    
    Args:
        db: Sesión de base de datos
        equipo_id: ID del equipo a actualizar
        equipo_in: Datos actualizados del equipo
        
    Returns:
        Equipo actualizado o None si no existe
    """
    # Obtener equipo existente
    stmt = select(Equipo).where(Equipo.id == equipo_id)
    result = await db.execute(stmt)
    db_equipo = result.scalar_one_or_none()
    
    if not db_equipo:
        return None
    
    # Convertir a diccionario si es un modelo Pydantic
    update_data = equipo_in if isinstance(equipo_in, dict) else equipo_in.model_dump(exclude_unset=True)
    
    # Actualizar fecha de última actualización
    update_data["fecha_ultima_actualizacion"] = datetime.now(timezone.utc)
    
    # Actualizar equipo
    for field, value in update_data.items():
        if hasattr(db_equipo, field):
            setattr(db_equipo, field, value)
    
    await db.commit()
    await db.refresh(db_equipo)
    
    # Obtener el equipo actualizado con sus relaciones
    return await get_equipo(db, db_equipo.id)


async def delete_equipo(db: AsyncSession, equipo_id: uuid.UUID) -> bool:
    """
    Elimina un equipo.
    
    Args:
        db: Sesión de base de datos
        equipo_id: ID del equipo a eliminar
        
    Returns:
        True si se eliminó correctamente, False en caso contrario
    """
    # Verificar que el equipo existe
    stmt = select(Equipo).where(Equipo.id == equipo_id)
    result = await db.execute(stmt)
    db_equipo = result.scalar_one_or_none()
    
    if not db_equipo:
        return False
    
    # Eliminar equipo
    await db.delete(db_equipo)
    await db.commit()
    
    return True


async def search_equipos(db: AsyncSession, termino: str) -> List[Dict[str, Any]]:
    """
    Busca equipos utilizando la funcionalidad de texto completo.
    
    Args:
        db: Sesión de base de datos
        termino: Término de búsqueda
        
    Returns:
        Lista de equipos encontrados con ranking de relevancia
    """
    # Preparar término de búsqueda para tsquery
    termino_query = termino.replace(' ', ' & ')
    
    # Consulta con ranking utilizando la función de búsqueda
    query = text(
        "SELECT id, nombre, numero_serie, marca, modelo, "
        "ts_rank(texto_busqueda, to_tsquery('spanish', :termino)) AS relevancia "
        "FROM control_equipos.equipos "
        "WHERE texto_busqueda @@ to_tsquery('spanish', :termino) "
        "ORDER BY relevancia DESC"
    )
    
    result = await db.execute(query, {"termino": termino_query})
    resultados = result.mappings().all()
    
    # Convertir a lista de diccionarios
    return [dict(r) for r in resultados]


# Servicios para Estados de Equipo
async def get_estados_equipo(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Obtiene todos los estados de equipo.
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        Lista de estados
    """
    stmt = select(EstadoEquipo)
    result = await db.execute(stmt)
    estados = result.scalars().all()
    
    return [estado.to_dict() for estado in estados]


async def create_estado_equipo(db: AsyncSession, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea un nuevo estado de equipo.
    
    Args:
        db: Sesión de base de datos
        data: Datos del estado a crear
        
    Returns:
        Estado creado
    """
    estado = EstadoEquipo(**data)
    db.add(estado)
    await db.commit()
    await db.refresh(estado)
    
    return estado.to_dict()


# Servicios para Proveedores
async def get_proveedores(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Obtiene todos los proveedores.
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        Lista de proveedores
    """
    stmt = select(Proveedor)
    result = await db.execute(stmt)
    proveedores = result.scalars().all()
    
    return [proveedor.to_dict() for proveedor in proveedores]


async def get_proveedor(db: AsyncSession, proveedor_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    """
    Obtiene un proveedor por su ID.
    
    Args:
        db: Sesión de base de datos
        proveedor_id: ID del proveedor
        
    Returns:
        Proveedor encontrado o None
    """
    stmt = select(Proveedor).where(Proveedor.id == proveedor_id)
    result = await db.execute(stmt)
    proveedor = result.scalar_one_or_none()
    
    return proveedor.to_dict() if proveedor else None


async def create_proveedor(db: AsyncSession, data: ProveedorCreate) -> Dict[str, Any]:
    """
    Crea un nuevo proveedor.
    
    Args:
        db: Sesión de base de datos
        data: Datos del proveedor a crear
        
    Returns:
        Proveedor creado
    """
    proveedor = Proveedor(**data.model_dump())
    db.add(proveedor)
    await db.commit()
    await db.refresh(proveedor)
    
    return proveedor.to_dict()


async def update_proveedor(
    db: AsyncSession, 
    proveedor_id: uuid.UUID, 
    data: ProveedorUpdate
) -> Optional[Dict[str, Any]]:
    """
    Actualiza un proveedor existente.
    
    Args:
        db: Sesión de base de datos
        proveedor_id: ID del proveedor a actualizar
        data: Datos actualizados del proveedor
        
    Returns:
        Proveedor actualizado o None si no existe
    """
    stmt = select(Proveedor).where(Proveedor.id == proveedor_id)
    result = await db.execute(stmt)
    proveedor = result.scalar_one_or_none()
    
    if not proveedor:
        return None
    
    update_data = data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if hasattr(proveedor, field):
            setattr(proveedor, field, value)
    
    await db.commit()
    await db.refresh(proveedor)
    
    return proveedor.to_dict()


async def delete_proveedor(db: AsyncSession, proveedor_id: uuid.UUID) -> bool:
    """
    Elimina un proveedor.
    
    Args:
        db: Sesión de base de datos
        proveedor_id: ID del proveedor a eliminar
        
    Returns:
        True si se eliminó correctamente, False en caso contrario
    """
    stmt = select(Proveedor).where(Proveedor.id == proveedor_id)
    result = await db.execute(stmt)
    proveedor = result.scalar_one_or_none()
    
    if not proveedor:
        return False
    
    await db.delete(proveedor)
    await db.commit()
    
    return True


# Servicios para Tipos de Documento
async def get_tipos_documento(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Obtiene todos los tipos de documento.
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        Lista de tipos de documento
    """
    stmt = select(TipoDocumento)
    result = await db.execute(stmt)
    tipos = result.scalars().all()
    
    return [tipo.to_dict() for tipo in tipos]


# Servicios para Documentación
async def get_documentos_equipo(
    db: AsyncSession, 
    equipo_id: uuid.UUID
) -> List[Dict[str, Any]]:
    """
    Obtiene los documentos asociados a un equipo.
    
    Args:
        db: Sesión de base de datos
        equipo_id: ID del equipo
        
    Returns:
        Lista de documentos
    """
    stmt = select(Documentacion).where(
        Documentacion.equipo_id == equipo_id
    ).options(
        joinedload(Documentacion.tipo_documento)
    )
    
    result = await db.execute(stmt)
    documentos = result.unique().scalars().all()
    
    # Convertir a lista de diccionarios con relaciones
    documentos_list = []
    for doc in documentos:
        doc_dict = doc.to_dict()
        
        if doc.tipo_documento:
            doc_dict["tipo_documento"] = doc.tipo_documento.to_dict()
            
        documentos_list.append(doc_dict)
        
    return documentos_list


async def create_documento(
    db: AsyncSession, 
    data: DocumentacionCreate, 
    usuario_id: uuid.UUID
) -> Dict[str, Any]:
    """
    Crea un nuevo documento para un equipo.
    
    Args:
        db: Sesión de base de datos
        data: Datos del documento a crear
        usuario_id: ID del usuario que sube el documento
        
    Returns:
        Documento creado
    """
    # Obtener tipo de documento para verificar si requiere verificación
    stmt = select(TipoDocumento).where(TipoDocumento.id == data.tipo_documento_id)
    result = await db.execute(stmt)
    tipo_documento = result.scalar_one_or_none()
    
    # Establecer estado inicial según el tipo de documento
    estado = "pendiente" if tipo_documento and tipo_documento.requiere_verificacion else "verificado"
    
    # Crear objeto de documento
    documento = Documentacion(
        **data.model_dump(),
        subido_por=usuario_id,
        estado=estado
    )
    
    db.add(documento)
    await db.commit()
    await db.refresh(documento)
    
    # Obtener el documento con sus relaciones
    return documento.to_dict()


async def get_documento(db: AsyncSession, documento_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    """
    Obtiene un documento por su ID.
    
    Args:
        db: Sesión de base de datos
        documento_id: ID del documento
        
    Returns:
        Documento encontrado o None
    """
    stmt = select(Documentacion).where(
        Documentacion.id == documento_id
    ).options(
        joinedload(Documentacion.tipo_documento)
    )
    
    result = await db.execute(stmt)
    documento = result.unique().scalar_one_or_none()
    
    if not documento:
        return None
        
    doc_dict = documento.to_dict()
    
    if documento.tipo_documento:
        doc_dict["tipo_documento"] = documento.tipo_documento.to_dict()
        
    return doc_dict


async def update_documento(
    db: AsyncSession, 
    documento_id: uuid.UUID, 
    data: DocumentacionUpdate
) -> Optional[Dict[str, Any]]:
    """
    Actualiza un documento existente.
    
    Args:
        db: Sesión de base de datos
        documento_id: ID del documento a actualizar
        data: Datos actualizados del documento
        
    Returns:
        Documento actualizado o None si no existe
    """
    stmt = select(Documentacion).where(Documentacion.id == documento_id)
    result = await db.execute(stmt)
    documento = result.scalar_one_or_none()
    
    if not documento:
        return None
    
    update_data = data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if hasattr(documento, field):
            setattr(documento, field, value)
    
    await db.commit()
    await db.refresh(documento)
    
    return await get_documento(db, documento_id)


async def verificar_documento(
    db: AsyncSession, 
    documento_id: uuid.UUID, 
    data: DocumentacionVerificar,
    verificador_id: uuid.UUID
) -> Optional[Dict[str, Any]]:
    """
    Verifica o rechaza un documento.
    
    Args:
        db: Sesión de base de datos
        documento_id: ID del documento a verificar
        data: Datos de verificación
        verificador_id: ID del usuario que verifica
        
    Returns:
        Documento actualizado o None si no existe
    """
    stmt = select(Documentacion).where(Documentacion.id == documento_id)
    result = await db.execute(stmt)
    documento = result.scalar_one_or_none()
    
    if not documento:
        return None
    
    # Actualizar estado y verificador
    documento.estado = data.estado
    documento.verificado_por = verificador_id
    documento.fecha_verificacion = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(documento)
    
    return await get_documento(db, documento_id)


async def delete_documento(db: AsyncSession, documento_id: uuid.UUID) -> bool:
    """
    Elimina un documento.
    
    Args:
        db: Sesión de base de datos
        documento_id: ID del documento a eliminar
        
    Returns:
        True si se eliminó correctamente, False en caso contrario
    """
    stmt = select(Documentacion).where(Documentacion.id == documento_id)
    result = await db.execute(stmt)
    documento = result.scalar_one_or_none()
    
    if not documento:
        return False
    
    await db.delete(documento)
    await db.commit()
    
    return True
