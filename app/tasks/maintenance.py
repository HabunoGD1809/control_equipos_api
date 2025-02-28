import uuid
from datetime import datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.logging import get_logger
from app.db.models.equipos import Equipo
from app.db.models.mantenimiento import Mantenimiento, TipoMantenimiento
from app.db.session import async_session_factory
from app.tasks.notifications import send_notification, send_role_notifications
from app.worker import register_task

logger = get_logger(__name__)


@register_task("check_upcoming_maintenances")
async def check_upcoming_maintenances(days_ahead: int = 7) -> None:
    """
    Verifica los mantenimientos programados próximos y envía notificaciones.
    
    Args:
        days_ahead: Número de días hacia adelante para verificar
    """
    logger.info(f"Verificando mantenimientos programados para los próximos {days_ahead} días")
    
    # Calcular fecha límite
    today = datetime.now(timezone.utc).date()
    limit_date = today + timedelta(days=days_ahead)
    
    async with async_session_factory() as session:
        # Buscar mantenimientos programados próximos
        stmt = select(Mantenimiento).where(
            and_(
                Mantenimiento.estado == "programado",
                Mantenimiento.fecha_mantenimiento >= today,
                Mantenimiento.fecha_mantenimiento <= limit_date
            )
        ).options(
            joinedload(Mantenimiento.equipo),
            joinedload(Mantenimiento.tipo_mantenimiento)
        )
        
        result = await session.execute(stmt)
        maintenances = result.unique().scalars().all()
        
        if not maintenances:
            logger.info("No se encontraron mantenimientos programados próximos")
            return
        
        # Enviar notificaciones
        for maintenance in maintenances:
            equipo_nombre = maintenance.equipo.nombre if maintenance.equipo else "Equipo desconocido"
            tipo_nombre = maintenance.tipo_mantenimiento.nombre if maintenance.tipo_mantenimiento else "Mantenimiento"
            fecha = maintenance.fecha_mantenimiento.strftime("%d/%m/%Y")
            
            mensaje = f"Mantenimiento próximo: {tipo_nombre} para {equipo_nombre} programado para el {fecha}"
            
            # Notificar a técnicos
            await send_role_notifications("tecnico", mensaje)
            
            # Notificar a supervisores
            await send_role_notifications("supervisor", mensaje)
            
        logger.info(f"Se enviaron notificaciones para {len(maintenances)} mantenimientos próximos")


@register_task("check_expired_maintenances")
async def check_expired_maintenances() -> None:
    """Verifica mantenimientos vencidos y envía notificaciones."""
    logger.info("Verificando mantenimientos vencidos")
    
    today = datetime.now(timezone.utc).date()
    
    async with async_session_factory() as session:
        # Buscar mantenimientos vencidos
        stmt = select(Mantenimiento).where(
            and_(
                Mantenimiento.estado.in_(["programado", "en_proceso"]),
                Mantenimiento.fecha_mantenimiento < today
            )
        ).options(
            joinedload(Mantenimiento.equipo),
            joinedload(Mantenimiento.tipo_mantenimiento)
        )
        
        result = await session.execute(stmt)
        maintenances = result.unique().scalars().all()
        
        if not maintenances:
            logger.info("No se encontraron mantenimientos vencidos")
            return
        
        # Enviar notificaciones
        for maintenance in maintenances:
            equipo_nombre = maintenance.equipo.nombre if maintenance.equipo else "Equipo desconocido"
            tipo_nombre = maintenance.tipo_mantenimiento.nombre if maintenance.tipo_mantenimiento else "Mantenimiento"
            fecha = maintenance.fecha_mantenimiento.strftime("%d/%m/%Y")
            
            mensaje = f"Mantenimiento vencido: {tipo_nombre} para {equipo_nombre} programado para el {fecha}"
            
            # Notificar a técnicos y supervisores
            await send_role_notifications("tecnico", mensaje)
            await send_role_notifications("supervisor", mensaje)
            
        logger.info(f"Se enviaron notificaciones para {len(maintenances)} mantenimientos vencidos")


@register_task("auto_schedule_maintenance")
async def auto_schedule_maintenance() -> None:
    """
    Programa automáticamente mantenimientos para equipos basados en tipos con periodicidad.
    """
    logger.info("Programando mantenimientos automáticos")
    
    async with async_session_factory() as session:
        # Buscar tipos de mantenimiento con periodicidad
        stmt = select(TipoMantenimiento).where(TipoMantenimiento.periodicidad_dias.isnot(None))
        result = await session.execute(stmt)
        maintenance_types = result.scalars().all()
        
        if not maintenance_types:
            logger.info("No se encontraron tipos de mantenimiento con periodicidad")
            return
        
        # Para cada tipo, buscar equipos que necesiten mantenimiento
        for mtype in maintenance_types:
            # Buscar últimos mantenimientos completados por equipo
            stmt = select(
                Mantenimiento.equipo_id,
                func.max(Mantenimiento.fecha_mantenimiento).label("ultima_fecha")
            ).where(
                and_(
                    Mantenimiento.tipo_mantenimiento_id == mtype.id,
                    Mantenimiento.estado == "completado"
                )
            ).group_by(Mantenimiento.equipo_id)
            
            result = await session.execute(stmt)
            last_maintenances = {row.equipo_id: row.ultima_fecha for row in result}
            
            # Buscar todos los equipos
            stmt = select(Equipo)
            result = await session.execute(stmt)
            equipos = result.scalars().all()
            
            # Contar programaciones
            scheduled_count = 0
            
            for equipo in equipos:
                # Verificar si el equipo ya tiene mantenimiento programado
                stmt = select(Mantenimiento).where(
                    and_(
                        Mantenimiento.equipo_id == equipo.id,
                        Mantenimiento.tipo_mantenimiento_id == mtype.id,
                        Mantenimiento.estado.in_(["programado", "en_proceso"])
                    )
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Ya tiene mantenimiento programado
                    continue
                
                # Obtener fecha del último mantenimiento
                last_date = last_maintenances.get(equipo.id)
                
                # Si nunca ha tenido mantenimiento o ha pasado la periodicidad
                if not last_date or (datetime.now(timezone.utc).date() - last_date) >= timedelta(days=mtype.periodicidad_dias):
                    # Programar mantenimiento para una semana después
                    next_date = datetime.now(timezone.utc).date() + timedelta(days=7)
                    
                    new_maintenance = Mantenimiento(
                        equipo_id=equipo.id,
                        tipo_mantenimiento_id=mtype.id,
                        fecha_mantenimiento=next_date,
                        estado="programado",
                        tecnico_responsable="Por asignar"
                    )
                    
                    session.add(new_maintenance)
                    scheduled_count += 1
            
            await session.commit()
            
            if scheduled_count > 0:
                logger.info(f"Se programaron {scheduled_count} mantenimientos para {mtype.nombre}")
                
                # Notificar a supervisores
                mensaje = f"Se programaron automáticamente {scheduled_count} mantenimientos de tipo {mtype.nombre}"
                await send_role_notifications("supervisor", mensaje)
