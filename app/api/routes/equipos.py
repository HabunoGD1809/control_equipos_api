from fastapi import APIRouter, Body, Depends, Path, Query, status
import uuid
from typing import Any, List, Optional

from app.api.deps import (
    CurrentUser, DbSession, DocumentosReadUser, DocumentosVerifyUser, 
    DocumentosWriteUser, EquiposReadUser, EquiposWriteUser
)
from app.core.error_handlers import NotFoundError, BadRequestError
from app.schemas.common import (
    ItemCreatedResponse, ItemDeletedResponse, 
    ItemResponse, ItemsResponse, ItemUpdatedResponse, 
    Mensaje, PaginatedResponse, SearchParams
)
from app.schemas.equipos import (
    Documentacion, DocumentacionCreate, DocumentacionUpdate, DocumentacionVerificar,
    Equipo, EquipoBusqueda, EquipoCreate, EquipoUpdate,
    EstadoEquipo, EstadoEquipoCreate, EstadoEquipoUpdate,
    Proveedor, ProveedorCreate, ProveedorUpdate,
    TipoDocumento, TipoDocumentoCreate, TipoDocumentoUpdate
)
from app.services.equipos import (
    create_documento, create_equipo, create_estado_equipo, create_proveedor,
    delete_documento, delete_equipo, delete_proveedor,
    get_documentos_equipo, get_documento, get_equipo, get_equipos,
    get_estados_equipo, get_proveedor, get_proveedores, get_tipos_documento,
    search_equipos, update_documento, update_equipo, update_proveedor,
    verificar_documento
)

router = APIRouter()


# Rutas para equipos
@router.get("/", response_model=PaginatedResponse[Equipo])
async def list_equipos(
    db: DbSession,
    current_user: EquiposReadUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    estado_id: Optional[uuid.UUID] = None,
    proveedor_id: Optional[uuid.UUID] = None,
    search: Optional[str] = None
) -> Any:
    """
    Obtiene la lista de equipos con filtros opcionales.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        skip: Número de registros a omitir (paginación)
        limit: Límite de registros a devolver
        estado_id: Filtrar por estado
        proveedor_id: Filtrar por proveedor
        search: Término de búsqueda
    """
    equipos = await get_equipos(
        db, skip=skip, limit=limit, 
        estado_id=estado_id, proveedor_id=proveedor_id, 
        search=search
    )
    
    # Obtener total para paginación
    total = len(await get_equipos(db)) if not (estado_id or proveedor_id or search) else len(equipos)
    
    return PaginatedResponse.create(
        items=equipos,
        total=total,
        page=(skip // limit) + 1,
        size=limit
    )


@router.post("/", response_model=ItemCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_new_equipo(
    db: DbSession,
    current_user: EquiposWriteUser,
    equipo_in: EquipoCreate = Body(...)
) -> Any:
    """
    Crea un nuevo equipo.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        equipo_in: Datos del equipo a crear
    """
    equipo = await create_equipo(db, equipo_in)
    
    return ItemCreatedResponse(
        id=equipo["id"],
        message="Equipo creado correctamente"
    )


@router.get("/{equipo_id}", response_model=ItemResponse[Equipo])
async def get_equipo_by_id(
    db: DbSession,
    current_user: EquiposReadUser,
    equipo_id: uuid.UUID = Path(...)
) -> Any:
    """
    Obtiene un equipo por su ID.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        equipo_id: ID del equipo
    """
    equipo = await get_equipo(db, equipo_id)
    
    if not equipo:
        raise NotFoundError("Equipo no encontrado")
    
    return ItemResponse(data=equipo)


@router.put("/{equipo_id}", response_model=ItemUpdatedResponse)
async def update_equipo_by_id(
    db: DbSession,
    current_user: EquiposWriteUser,
    equipo_in: EquipoUpdate,
    equipo_id: uuid.UUID = Path(...)
) -> Any:
    """
    Actualiza un equipo existente.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        equipo_in: Datos actualizados del equipo
        equipo_id: ID del equipo a actualizar
    """
    equipo = await get_equipo(db, equipo_id)
    
    if not equipo:
        raise NotFoundError("Equipo no encontrado")
    
    equipo_actualizado = await update_equipo(db, equipo_id, equipo_in)
    
    return ItemUpdatedResponse(
        id=equipo_id,
        message="Equipo actualizado correctamente"
    )


@router.delete("/{equipo_id}", response_model=ItemDeletedResponse)
async def delete_equipo_by_id(
    db: DbSession,
    current_user: EquiposWriteUser,
    equipo_id: uuid.UUID = Path(...)
) -> Any:
    """
    Elimina un equipo.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        equipo_id: ID del equipo a eliminar
    """
    eliminado = await delete_equipo(db, equipo_id)
    
    if not eliminado:
        raise NotFoundError("Equipo no encontrado")
    
    return ItemDeletedResponse(
        id=equipo_id,
        message="Equipo eliminado correctamente"
    )


@router.get("/search/text", response_model=ItemsResponse[EquipoBusqueda])
async def search_equipos_text(
    db: DbSession,
    current_user: EquiposReadUser,
    search_params: SearchParams = Depends()
) -> Any:
    """
    Busca equipos utilizando búsqueda de texto completo.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        search_params: Parámetros de búsqueda
    """
    if not search_params.q:
        raise BadRequestError("Se requiere un término de búsqueda")
    
    resultados = await search_equipos(db, search_params.q)
    
    # Aplicar paginación en memoria
    total = len(resultados)
    resultados = resultados[search_params.skip:search_params.skip + search_params.limit]
    
    return ItemsResponse(data=resultados)


# Rutas para documentos de equipos
@router.get("/{equipo_id}/documentos", response_model=ItemsResponse[Documentacion])
async def get_documentos_de_equipo(
    db: DbSession,
    current_user: DocumentosReadUser,
    equipo_id: uuid.UUID = Path(...)
) -> Any:
    """
    Obtiene los documentos asociados a un equipo.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        equipo_id: ID del equipo
    """
    equipo = await get_equipo(db, equipo_id)
    
    if not equipo:
        raise NotFoundError("Equipo no encontrado")
    
    documentos = await get_documentos_equipo(db, equipo_id)
    
    return ItemsResponse(data=documentos)


@router.post("/{equipo_id}/documentos", response_model=ItemCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_documento_equipo(
    db: DbSession,
    current_user: DocumentosWriteUser,
    equipo_id: uuid.UUID = Path(...),
    documento_in: DocumentacionCreate = Body(...)
) -> Any:
    """
    Crea un nuevo documento para un equipo.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        equipo_id: ID del equipo
        documento_in: Datos del documento a crear
    """
    # Verificar que el equipo existe
    equipo = await get_equipo(db, equipo_id)
    
    if not equipo:
        raise NotFoundError("Equipo no encontrado")
    
    # Verificar que el equipo_id en el documento coincide con el de la ruta
    if documento_in.equipo_id != equipo_id:
        raise BadRequestError("El ID del equipo en el documento no coincide con el de la ruta")
    
    documento = await create_documento(db, documento_in, current_user["id"])
    
    return ItemCreatedResponse(
        id=documento["id"],
        message="Documento creado correctamente"
    )


@router.get("/{equipo_id}/documentos/{documento_id}", response_model=ItemResponse[Documentacion])
async def get_documento_equipo(
    db: DbSession,
    current_user: DocumentosReadUser,
    equipo_id: uuid.UUID = Path(...),
    documento_id: uuid.UUID = Path(...)
) -> Any:
    """
    Obtiene un documento específico de un equipo.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        equipo_id: ID del equipo
        documento_id: ID del documento
    """
    documento = await get_documento(db, documento_id)
    
    if not documento:
        raise NotFoundError("Documento no encontrado")
    
    # Verificar que el documento pertenece al equipo
    if documento["equipo_id"] != equipo_id:
        raise BadRequestError("El documento no pertenece al equipo especificado")
    
    return ItemResponse(data=documento)


@router.put("/{equipo_id}/documentos/{documento_id}", response_model=ItemUpdatedResponse)
async def update_documento_equipo(
    db: DbSession,
    current_user: DocumentosWriteUser,
    equipo_id: uuid.UUID = Path(...),
    documento_id: uuid.UUID = Path(...),
    documento_in: DocumentacionUpdate = Body(...)
) -> Any:
    """
    Actualiza un documento de un equipo.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        equipo_id: ID del equipo
        documento_id: ID del documento
        documento_in: Datos actualizados del documento
    """
    documento = await get_documento(db, documento_id)
    
    if not documento:
        raise NotFoundError("Documento no encontrado")
    
    # Verificar que el documento pertenece al equipo
    if documento["equipo_id"] != equipo_id:
        raise BadRequestError("El documento no pertenece al equipo especificado")
    
    documento_actualizado = await update_documento(db, documento_id, documento_in)
    
    return ItemUpdatedResponse(
        id=documento_id,
        message="Documento actualizado correctamente"
    )


@router.delete("/{equipo_id}/documentos/{documento_id}", response_model=ItemDeletedResponse)
async def delete_documento_equipo(
    db: DbSession,
    current_user: DocumentosWriteUser,
    equipo_id: uuid.UUID = Path(...),
    documento_id: uuid.UUID = Path(...)
) -> Any:
    """
    Elimina un documento de un equipo.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        equipo_id: ID del equipo
        documento_id: ID del documento
    """
    documento = await get_documento(db, documento_id)
    
    if not documento:
        raise NotFoundError("Documento no encontrado")
    
    # Verificar que el documento pertenece al equipo
    if documento["equipo_id"] != equipo_id:
        raise BadRequestError("El documento no pertenece al equipo especificado")
    
    eliminado = await delete_documento(db, documento_id)
    
    return ItemDeletedResponse(
        id=documento_id,
        message="Documento eliminado correctamente"
    )


@router.post("/{equipo_id}/documentos/{documento_id}/verificar", response_model=ItemUpdatedResponse)
async def verificar_documento_equipo(
    db: DbSession,
    current_user: DocumentosVerifyUser,
    equipo_id: uuid.UUID = Path(...),
    documento_id: uuid.UUID = Path(...),
    verificacion: DocumentacionVerificar = Body(...)
) -> Any:
    """
    Verifica o rechaza un documento de un equipo.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        equipo_id: ID del equipo
        documento_id: ID del documento
        verificacion: Datos de verificación
    """
    documento = await get_documento(db, documento_id)
    
    if not documento:
        raise NotFoundError("Documento no encontrado")
    
    # Verificar que el documento pertenece al equipo
    if documento["equipo_id"] != equipo_id:
        raise BadRequestError("El documento no pertenece al equipo especificado")
    
    # Verificar que el documento está pendiente
    if documento["estado"] != "pendiente":
        raise BadRequestError("El documento ya ha sido verificado o rechazado")
    
    documento_actualizado = await verificar_documento(
        db, documento_id, verificacion, current_user["id"]
    )
    
    accion = "verificado" if verificacion.estado == "verificado" else "rechazado"
    
    return ItemUpdatedResponse(
        id=documento_id,
        message=f"Documento {accion} correctamente"
    )


# Rutas para estados de equipo
@router.get("/estados/all", response_model=ItemsResponse[EstadoEquipo])
async def list_estados_equipo(
    db: DbSession,
    current_user: EquiposReadUser
) -> Any:
    """
    Obtiene todos los estados de equipo disponibles.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
    """
    estados = await get_estados_equipo(db)
    
    return ItemsResponse(data=estados)


@router.post("/estados", response_model=ItemCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_estado(
    db: DbSession,
    current_user: EquiposWriteUser,
    estado_in: EstadoEquipoCreate = Body(...)
) -> Any:
    """
    Crea un nuevo estado de equipo.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        estado_in: Datos del estado a crear
    """
    estado = await create_estado_equipo(db, estado_in.model_dump())
    
    return ItemCreatedResponse(
        id=estado["id"],
        message="Estado de equipo creado correctamente"
    )


# Rutas para proveedores
@router.get("/proveedores/all", response_model=ItemsResponse[Proveedor])
async def list_proveedores(
    db: DbSession,
    current_user: EquiposReadUser
) -> Any:
    """
    Obtiene todos los proveedores disponibles.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
    """
    proveedores = await get_proveedores(db)
    
    return ItemsResponse(data=proveedores)


@router.post("/proveedores", response_model=ItemCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_proveedor_route(
    db: DbSession,
    current_user: EquiposWriteUser,
    proveedor_in: ProveedorCreate = Body(...)
) -> Any:
    """
    Crea un nuevo proveedor.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        proveedor_in: Datos del proveedor a crear
    """
    proveedor = await create_proveedor(db, proveedor_in)
    
    return ItemCreatedResponse(
        id=proveedor["id"],
        message="Proveedor creado correctamente"
    )


@router.get("/proveedores/{proveedor_id}", response_model=ItemResponse[Proveedor])
async def get_proveedor_by_id(
    db: DbSession,
    current_user: EquiposReadUser,
    proveedor_id: uuid.UUID = Path(...)
) -> Any:
    """
    Obtiene un proveedor por su ID.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        proveedor_id: ID del proveedor
    """
    proveedor = await get_proveedor(db, proveedor_id)
    
    if not proveedor:
        raise NotFoundError("Proveedor no encontrado")
    
    return ItemResponse(data=proveedor)


@router.put("/proveedores/{proveedor_id}", response_model=ItemUpdatedResponse)
async def update_proveedor_by_id(
    db: DbSession,
    current_user: EquiposWriteUser,
    proveedor_id: uuid.UUID = Path(...),
    proveedor_in: ProveedorUpdate = Body(...)
) -> Any:
    """
    Actualiza un proveedor existente.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        proveedor_id: ID del proveedor a actualizar
        proveedor_in: Datos actualizados del proveedor
    """
    proveedor = await get_proveedor(db, proveedor_id)
    
    if not proveedor:
        raise NotFoundError("Proveedor no encontrado")
    
    proveedor_actualizado = await update_proveedor(db, proveedor_id, proveedor_in)
    
    return ItemUpdatedResponse(
        id=proveedor_id,
        message="Proveedor actualizado correctamente"
    )


@router.delete("/proveedores/{proveedor_id}", response_model=ItemDeletedResponse)
async def delete_proveedor_by_id(
    db: DbSession,
    current_user: EquiposWriteUser,
    proveedor_id: uuid.UUID = Path(...)
) -> Any:
    """
    Elimina un proveedor.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        proveedor_id: ID del proveedor a eliminar
    """
    eliminado = await delete_proveedor(db, proveedor_id)
    
    if not eliminado:
        raise NotFoundError("Proveedor no encontrado")
    
    return ItemDeletedResponse(
        id=proveedor_id,
        message="Proveedor eliminado correctamente"
    )


# Rutas para tipos de documento
@router.get("/tipos-documento/all", response_model=ItemsResponse[TipoDocumento])
async def list_tipos_documento(
    db: DbSession,
    current_user: DocumentosReadUser
) -> Any:
    """
    Obtiene todos los tipos de documento disponibles.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
    """
    tipos = await get_tipos_documento(db)
    
    return ItemsResponse(data=tipos)
