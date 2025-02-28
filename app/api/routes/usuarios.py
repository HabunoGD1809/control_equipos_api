from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
import uuid
from typing import Any, List, Optional

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.core.error_handlers import NotFoundError
from app.schemas.common import (
    ItemCreatedResponse, ItemDeletedResponse, 
    ItemResponse, ItemsResponse, ItemUpdatedResponse, 
    Mensaje, PaginatedResponse
)
from app.schemas.usuarios import (
    Notificacion, Permiso, Rol, Usuario, 
    UsuarioChangePassword, UsuarioCreate, UsuarioUpdate
)
from app.services.usuarios import (
    change_user_password, create_user, delete_user, 
    get_permisos, get_roles, get_user, get_users, 
    get_user_notifications, mark_notification_as_read,
    update_user
)

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[Usuario])
async def list_usuarios(
    db: DbSession,
    current_user: AdminUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    role_id: Optional[uuid.UUID] = None,
    search: Optional[str] = None
) -> Any:
    """
    Obtiene la lista de usuarios.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        skip: Número de registros a omitir (paginación)
        limit: Límite de registros a devolver
        role_id: Filtrar por rol
        search: Término de búsqueda
    """
    usuarios = await get_users(db, skip=skip, limit=limit, role_id=role_id, search=search)
    
    # (Deberia, en un sistema real usarías count query optimizado)
    total = len(await get_users(db)) if not role_id and not search else len(usuarios)
    
    return PaginatedResponse.create(
        items=usuarios,
        total=total,
        page=(skip // limit) + 1,
        size=limit
    )


@router.post("/", response_model=ItemCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_usuario(
    db: DbSession,
    current_user: AdminUser,
    usuario_in: UsuarioCreate = Body(...)
) -> Any:
    """
    Crea un nuevo usuario.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        usuario_in: Datos del usuario a crear
    """
    usuario = await create_user(db, usuario_in)
    
    return ItemCreatedResponse(
        id=usuario["id"],
        message="Usuario creado correctamente"
    )


@router.get("/{usuario_id}", response_model=ItemResponse[Usuario])
async def get_usuario(
    db: DbSession,
    current_user: AdminUser,
    usuario_id: uuid.UUID = Path(...)
) -> Any:
    """
    Obtiene un usuario por su ID.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        usuario_id: ID del usuario
    """
    usuario = await get_user(db, usuario_id)
    
    if not usuario:
        raise NotFoundError("Usuario no encontrado")
    
    return ItemResponse(data=usuario)


@router.put("/{usuario_id}", response_model=ItemUpdatedResponse)
async def update_usuario(
    db: DbSession,
    current_user: AdminUser,
    usuario_in: UsuarioUpdate,
    usuario_id: uuid.UUID = Path(...)
) -> Any:
    """
    Actualiza un usuario existente.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        usuario_in: Datos actualizados del usuario
        usuario_id: ID del usuario a actualizar
    """
    usuario = await get_user(db, usuario_id)
    
    if not usuario:
        raise NotFoundError("Usuario no encontrado")
    
    usuario_actualizado = await update_user(db, usuario_id, usuario_in)
    
    return ItemUpdatedResponse(
        id=usuario_id,
        message="Usuario actualizado correctamente"
    )


@router.delete("/{usuario_id}", response_model=ItemDeletedResponse)
async def delete_usuario(
    db: DbSession,
    current_user: AdminUser,
    usuario_id: uuid.UUID = Path(...)
) -> Any:
    """
    Elimina un usuario.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        usuario_id: ID del usuario a eliminar
    """
    # Verificar que no se está eliminando a sí mismo
    if usuario_id == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminar tu propio usuario"
        )
    
    eliminado = await delete_user(db, usuario_id)
    
    if not eliminado:
        raise NotFoundError("Usuario no encontrado")
    
    return ItemDeletedResponse(
        id=usuario_id,
        message="Usuario eliminado correctamente"
    )


@router.get("/me/profile", response_model=ItemResponse[Usuario])
async def get_current_user_profile(
    db: DbSession,
    current_user: CurrentUser
) -> Any:
    """
    Obtiene el perfil del usuario actual.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
    """
    usuario = await get_user(db, current_user["id"])
    
    if not usuario:
        raise NotFoundError("Usuario no encontrado")
    
    return ItemResponse(data=usuario)


@router.put("/me/password", response_model=Mensaje)
async def change_current_user_password(
    db: DbSession,
    current_user: CurrentUser,
    password_in: UsuarioChangePassword
) -> Any:
    """
    Cambia la contraseña del usuario actual.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        password_in: Datos para cambio de contraseña
    """
    if password_in.confirmar_contrasena != password_in.nueva_contrasena:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Las contraseñas no coinciden"
        )
    
    cambiada = await change_user_password(
        db, 
        current_user["id"], 
        password_in.contrasena_actual, 
        password_in.nueva_contrasena
    )
    
    if not cambiada:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contraseña actual incorrecta"
        )
    
    return {"detail": "Contraseña actualizada correctamente"}


@router.get("/me/notifications", response_model=ItemsResponse[Notificacion])
async def get_current_user_notifications(
    db: DbSession,
    current_user: CurrentUser,
    unread_only: bool = Query(False)
) -> Any:
    """
    Obtiene las notificaciones del usuario actual.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        unread_only: Si solo se deben devolver las notificaciones no leídas
    """
    notificaciones = await get_user_notifications(db, current_user["id"], unread_only)
    
    return ItemsResponse(data=notificaciones)


@router.post("/me/notifications/{notification_id}/read", response_model=Mensaje)
async def mark_notification_read(
    db: DbSession,
    current_user: CurrentUser,
    notification_id: uuid.UUID = Path(...)
) -> Any:
    """
    Marca una notificación como leída.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
        notification_id: ID de la notificación
    """
    notificacion = await mark_notification_as_read(db, notification_id)
    
    if not notificacion:
        raise NotFoundError("Notificación no encontrada")
    
    return {"detail": "Notificación marcada como leída correctamente"}


@router.get("/roles", response_model=ItemsResponse[Rol])
async def list_roles(
    db: DbSession,
    current_user: AdminUser
) -> Any:
    """
    Obtiene la lista de roles disponibles.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
    """
    roles = await get_roles(db)
    
    return ItemsResponse(data=roles)


@router.get("/permisos", response_model=ItemsResponse[Permiso])
async def list_permisos(
    db: DbSession,
    current_user: AdminUser
) -> Any:
    """
    Obtiene la lista de permisos disponibles.
    
    Args:
        db: Sesión de base de datos
        current_user: Usuario autenticado
    """
    permisos = await get_permisos(db)
    
    return ItemsResponse(data=permisos)
