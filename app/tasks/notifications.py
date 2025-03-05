import asyncio
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.usuarios import Notificacion, Usuario
from app.db.session import async_session_factory
from app.worker import register_task

logger = get_logger(__name__)


@register_task("send_notification")
async def send_notification(
    user_id: uuid.UUID,
    message: str,
    related_entity_id: Optional[uuid.UUID] = None
) -> None:
    """
    Envía una notificación a un usuario.
    
    Args:
        user_id: ID del usuario destinatario
        message: Mensaje de la notificación
        related_entity_id: ID de la entidad relacionada (opcional)
    """
    logger.info(f"Enviando notificación al usuario {user_id}: {message}")
    
    async with async_session_factory() as session:
        # Verificar que el usuario existe
        user = await session.get(Usuario, user_id)
        if not user:
            logger.warning(f"Usuario no encontrado: {user_id}")
            return
        
        # Crear notificación
        notification = Notificacion(
            usuario_id=user_id,
            mensaje=message,
            leido=False,
            created_at=datetime.now(timezone.utc)
        )
        
        session.add(notification)
        await session.commit()
        
        logger.info(f"Notificación enviada correctamente: {notification.id}")


@register_task("send_bulk_notifications")
async def send_bulk_notifications(
    user_ids: List[uuid.UUID],
    message: str
) -> None:
    """
    Envía notificaciones a múltiples usuarios.
    
    Args:
        user_ids: Lista de IDs de usuarios destinatarios
        message: Mensaje de la notificación
    """
    logger.info(f"Enviando notificación a {len(user_ids)} usuarios")
    
    # Usar asyncio.gather para enviar notificaciones en paralelo
    tasks = [
        send_notification(user_id, message)
        for user_id in user_ids
    ]
    
    await asyncio.gather(*tasks)
    
    logger.info(f"Notificaciones masivas enviadas correctamente")


@register_task("send_role_notifications")
async def send_role_notifications(
    role_name: str,
    message: str
) -> None:
    """
    Envía notificaciones a todos los usuarios con un rol específico.
    
    Args:
        role_name: Nombre del rol
        message: Mensaje de la notificación
    """
    logger.info(f"Enviando notificación a usuarios con rol: {role_name}")
    
    async with async_session_factory() as session:
        # Buscar usuarios con el rol especificado
        stmt = select(Usuario).join(Usuario.rol).where(Usuario.rol.has(nombre=role_name))
        result = await session.execute(stmt)
        users = result.scalars().all()
        
        if not users:
            logger.warning(f"No se encontraron usuarios con el rol: {role_name}")
            return
        
        # Enviar notificaciones
        user_ids = [user.id for user in users]
        await send_bulk_notifications(user_ids, message)
        
        logger.info(f"Notificaciones enviadas a {len(user_ids)} usuarios con rol {role_name}")


@register_task("mark_old_notifications_as_read")
async def mark_old_notifications_as_read(days: int = 30) -> None:
    """
    Marca como leídas las notificaciones antiguas no leídas.
    
    Args:
        days: Número de días para considerar notificaciones como antiguas
    """
    logger.info(f"Marcando notificaciones antiguas como leídas ({days} días)")
    
    # Calcular fecha límite
    cutoff_date = datetime.now(timezone.utc) - datetime.timedelta(days=days)
    
    async with async_session_factory() as session:
        # Buscar notificaciones antiguas no leídas
        stmt = select(Notificacion).where(
            Notificacion.leido == False,
            Notificacion.created_at < cutoff_date
        )
        result = await session.execute(stmt)
        notifications = result.scalars().all()
        
        if not notifications:
            logger.info("No se encontraron notificaciones antiguas")
            return
        
        # Marcar como leídas
        for notification in notifications:
            notification.leido = True
            notification.fecha_leido = datetime.now(timezone.utc)
        
        await session.commit()
        
        logger.info(f"Se marcaron {len(notifications)} notificaciones antiguas como leídas")
