from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.password import get_password_hash, verify_password
from app.db.models.usuarios import LoginLog, Notificacion, Permiso, Rol, Usuario
from app.schemas.usuarios import UsuarioCreate, UsuarioUpdate


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene un usuario por su nombre de usuario.
    
    Args:
        db: Sesión de base de datos
        username: Nombre de usuario
        
    Returns:
        Usuario encontrado o None
    """
    # Consultar usuario y sus relaciones
    stmt = select(Usuario).where(Usuario.nombre_usuario == username).options(
        joinedload(Usuario.rol).selectinload(Rol.permisos)
    )
    result = await db.execute(stmt)
    user = result.unique().scalar_one_or_none()
    
    if not user:
        return None
        
    # Convertir a diccionario y agregar rol y permisos
    user_dict = user.to_dict()
    
    # Agregar información del rol
    if user.rol:
        user_dict["rol"] = user.rol.to_dict()
        user_dict["rol"]["permisos"] = [p.to_dict() for p in user.rol.permisos]
        
    return user_dict


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene un usuario por su correo electrónico.
    
    Args:
        db: Sesión de base de datos
        email: Correo electrónico
        
    Returns:
        Usuario encontrado o None
    """
    stmt = select(Usuario).where(Usuario.email == email).options(
        joinedload(Usuario.rol).selectinload(Rol.permisos)
    )
    result = await db.execute(stmt)
    user = result.unique().scalar_one_or_none()
    
    if not user:
        return None
        
    user_dict = user.to_dict()
    
    if user.rol:
        user_dict["rol"] = user.rol.to_dict()
        user_dict["rol"]["permisos"] = [p.to_dict() for p in user.rol.permisos]
        
    return user_dict


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    """
    Obtiene un usuario por su ID.
    
    Args:
        db: Sesión de base de datos
        user_id: ID del usuario
        
    Returns:
        Usuario encontrado o None
    """
    stmt = select(Usuario).where(Usuario.id == user_id).options(
        joinedload(Usuario.rol).selectinload(Rol.permisos)
    )
    result = await db.execute(stmt)
    user = result.unique().scalar_one_or_none()
    
    if not user:
        return None
        
    user_dict = user.to_dict()
    
    if user.rol:
        user_dict["rol"] = user.rol.to_dict()
        user_dict["rol"]["permisos"] = [p.to_dict() for p in user.rol.permisos]
        
    return user_dict


async def get_users(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    role_id: Optional[uuid.UUID] = None,
    search: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Obtiene una lista de usuarios con filtros opcionales.
    
    Args:
        db: Sesión de base de datos
        skip: Número de registros a omitir (paginación)
        limit: Límite de registros a devolver
        role_id: Filtrar por ID de rol
        search: Término de búsqueda
        
    Returns:
        Lista de usuarios
    """
    # Construir consulta base
    query = select(Usuario).options(
        joinedload(Usuario.rol)
    )
    
    # Aplicar filtros
    if role_id:
        query = query.where(Usuario.rol_id == role_id)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (Usuario.nombre_usuario.ilike(search_term)) |
            (Usuario.email.ilike(search_term))
        )
    
    # Aplicar paginación
    query = query.offset(skip).limit(limit)
    
    # Ejecutar consulta
    result = await db.execute(query)
    users = result.unique().scalars().all()
    
    # Convertir a lista de diccionarios
    users_list = []
    for user in users:
        user_dict = user.to_dict()
        # Omitir contraseña por seguridad
        user_dict.pop("contrasena", None)
        
        if user.rol:
            user_dict["rol"] = user.rol.to_dict()
            
        users_list.append(user_dict)
        
    return users_list


async def create_user(db: AsyncSession, user_in: UsuarioCreate) -> Dict[str, Any]:
    """
    Crea un nuevo usuario.
    
    Args:
        db: Sesión de base de datos
        user_in: Datos del usuario a crear
        
    Returns:
        Usuario creado
    """
    # Hashear contraseña
    hashed_password = get_password_hash(user_in.contrasena)
    
    # Crear objeto de usuario
    db_user = Usuario(
        nombre_usuario=user_in.nombre_usuario,
        email=user_in.email,
        contrasena=hashed_password,
        rol_id=user_in.rol_id,
        requiere_cambio_contrasena=user_in.requiere_cambio_contrasena
    )
    
    # Guardar en la base de datos
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    # Convertir a diccionario
    user_dict = db_user.to_dict()
    # Omitir contraseña por seguridad
    user_dict.pop("contrasena", None)
    
    return user_dict


async def update_user(
    db: AsyncSession, 
    user_id: uuid.UUID, 
    obj_in: Union[UsuarioUpdate, Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Actualiza un usuario existente.
    
    Args:
        db: Sesión de base de datos
        user_id: ID del usuario a actualizar
        obj_in: Datos actualizados del usuario
        
    Returns:
        Usuario actualizado o None si no existe
    """
    # Obtener usuario existente
    stmt = select(Usuario).where(Usuario.id == user_id)
    result = await db.execute(stmt)
    db_user = result.scalar_one_or_none()
    
    if not db_user:
        return None
    
    # Convertir a diccionario si es un modelo Pydantic
    update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)
    
    # Si incluye contraseña, hashearla
    if "contrasena" in update_data:
        update_data["contrasena"] = get_password_hash(update_data["contrasena"])
    
    # Actualizar usuario
    for field, value in update_data.items():
        if hasattr(db_user, field):
            setattr(db_user, field, value)
    
    await db.commit()
    await db.refresh(db_user)
    
    # Convertir a diccionario
    user_dict = db_user.to_dict()
    # Omitir contraseña por seguridad
    user_dict.pop("contrasena", None)
    
    return user_dict


async def delete_user(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """
    Elimina un usuario.
    
    Args:
        db: Sesión de base de datos
        user_id: ID del usuario a eliminar
        
    Returns:
        True si se eliminó correctamente, False en caso contrario
    """
    # Verificar que el usuario existe
    stmt = select(Usuario).where(Usuario.id == user_id)
    result = await db.execute(stmt)
    db_user = result.scalar_one_or_none()
    
    if not db_user:
        return False
    
    # Eliminar usuario
    await db.delete(db_user)
    await db.commit()
    
    return True


async def register_login_attempt(
    db: AsyncSession, 
    user_id: Optional[uuid.UUID], 
    success: bool,
    ip_address: Optional[str] = None
) -> None:
    """
    Registra un intento de inicio de sesión.
    
    Args:
        db: Sesión de base de datos
        user_id: ID del usuario (puede ser None para intentos con usuarios inexistentes)
        success: Si el intento fue exitoso
        ip_address: Dirección IP del cliente (opcional)
        
    Returns:
        None
    """
    login_log = LoginLog(
        usuario_id=user_id,
        exito=success,
        ip_origen=ip_address
    )
    
    db.add(login_log)
    await db.commit()


async def create_notification(
    db: AsyncSession, 
    user_id: uuid.UUID, 
    message: str
) -> Dict[str, Any]:
    """
    Crea una notificación para un usuario.
    
    Args:
        db: Sesión de base de datos
        user_id: ID del usuario destinatario
        message: Mensaje de la notificación
        
    Returns:
        Notificación creada
    """
    notification = Notificacion(
        usuario_id=user_id,
        mensaje=message
    )
    
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    
    return notification.to_dict()


async def mark_notification_as_read(
    db: AsyncSession, 
    notification_id: uuid.UUID
) -> Optional[Dict[str, Any]]:
    """
    Marca una notificación como leída.
    
    Args:
        db: Sesión de base de datos
        notification_id: ID de la notificación
        
    Returns:
        Notificación actualizada o None si no existe
    """
    # Obtener notificación
    stmt = select(Notificacion).where(Notificacion.id == notification_id)
    result = await db.execute(stmt)
    notification = result.scalar_one_or_none()
    
    if not notification:
        return None
    
    # Marcar como leída
    notification.leido = True
    notification.fecha_leido = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(notification)
    
    return notification.to_dict()


async def get_user_notifications(
    db: AsyncSession, 
    user_id: uuid.UUID,
    unread_only: bool = False
) -> List[Dict[str, Any]]:
    """
    Obtiene las notificaciones de un usuario.
    
    Args:
        db: Sesión de base de datos
        user_id: ID del usuario
        unread_only: Si solo se deben devolver las notificaciones no leídas
        
    Returns:
        Lista de notificaciones
    """
    # Construir consulta
    query = select(Notificacion).where(Notificacion.usuario_id == user_id)
    
    if unread_only:
        query = query.where(Notificacion.leido == False)
    
    # Ordenar por fecha de creación (más recientes primero)
    query = query.order_by(Notificacion.created_at.desc())
    
    # Ejecutar consulta
    result = await db.execute(query)
    notifications = result.scalars().all()
    
    # Convertir a lista de diccionarios
    return [n.to_dict() for n in notifications]


async def get_user_login_history(
    db: AsyncSession, 
    user_id: uuid.UUID,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Obtiene el historial de inicios de sesión de un usuario.
    
    Args:
        db: Sesión de base de datos
        user_id: ID del usuario
        limit: Número máximo de registros a devolver
        
    Returns:
        Lista de registros de inicio de sesión
    """
    # Construir consulta
    query = select(LoginLog).where(LoginLog.usuario_id == user_id)
    
    # Ordenar por fecha (más recientes primero) y limitar resultados
    query = query.order_by(LoginLog.intento.desc()).limit(limit)
    
    # Ejecutar consulta
    result = await db.execute(query)
    login_logs = result.scalars().all()
    
    # Convertir a lista de diccionarios
    return [log.to_dict() for log in login_logs]


async def change_user_password(
    db: AsyncSession,
    user_id: uuid.UUID,
    current_password: str,
    new_password: str
) -> bool:
    """
    Cambia la contraseña de un usuario.
    
    Args:
        db: Sesión de base de datos
        user_id: ID del usuario
        current_password: Contraseña actual
        new_password: Nueva contraseña
        
    Returns:
        True si el cambio fue exitoso, False en caso contrario
    """
    # Obtener usuario
    stmt = select(Usuario).where(Usuario.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        return False
    
    # Verificar contraseña actual
    if not verify_password(current_password, user.contrasena):
        return False
    
    # Actualizar contraseña
    user.contrasena = get_password_hash(new_password)
    user.requiere_cambio_contrasena = False
    user.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    return True


async def get_roles(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Obtiene todos los roles disponibles.
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        Lista de roles
    """
    # Obtener roles con sus permisos
    stmt = select(Rol).options(selectinload(Rol.permisos))
    result = await db.execute(stmt)
    roles = result.scalars().all()
    
    # Convertir a lista de diccionarios
    roles_list = []
    for role in roles:
        role_dict = role.to_dict()
        role_dict["permisos"] = [p.to_dict() for p in role.permisos]
        roles_list.append(role_dict)
        
    return roles_list


async def get_permisos(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Obtiene todos los permisos disponibles.
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        Lista de permisos
    """
    stmt = select(Permiso)
    result = await db.execute(stmt)
    permisos = result.scalars().all()
    
    return [p.to_dict() for p in permisos]
