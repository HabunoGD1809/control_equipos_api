import csv
import io
import os
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.core.logging import get_logger
from app.db.models.equipos import Equipo, EstadoEquipo
from app.db.models.mantenimiento import Mantenimiento
from app.db.models.movimientos import Movimiento
from app.db.session import async_session_factory
from app.tasks.notifications import send_role_notifications
from app.worker import register_task

logger = get_logger(__name__)

# Directorio para reportes
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)


@register_task("generate_equipment_status_report")
async def generate_equipment_status_report() -> str:
    """
    Genera un reporte del estado actual de todos los equipos.
    
    Returns:
        Ruta al archivo de reporte generado
    """
    logger.info("Generando reporte de estado de equipos")
    
    # Fecha y nombre de archivo
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"equipos_estado_{today}.csv"
    filepath = REPORTS_DIR / filename
    
    async with async_session_factory() as session:
        # Obtener todos los equipos con sus estados
        stmt = select(Equipo).options(
            joinedload(Equipo.estado),
            joinedload(Equipo.proveedor)
        )
        result = await session.execute(stmt)
        equipos = result.unique().scalars().all()
        
        # Crear archivo CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'ID', 'Nombre', 'Número de Serie', 'Estado', 'Ubicación Actual', 
                'Marca', 'Modelo', 'Fecha Adquisición', 'Garantía', 'Días Garantía', 
                'Proveedor'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for equipo in equipos:
                # Calcular días de garantía restantes
                dias_garantia = None
                if equipo.fecha_garantia_expiracion:
                    dias = (equipo.fecha_garantia_expiracion - datetime.now(timezone.utc).date()).days
                    dias_garantia = max(0, dias)
                
                writer.writerow({
                    'ID': str(equipo.id),
                    'Nombre': equipo.nombre,
                    'Número de Serie': equipo.numero_serie,
                    'Estado': equipo.estado.nombre if equipo.estado else 'Desconocido',
                    'Ubicación Actual': equipo.ubicacion_actual or 'No especificada',
                    'Marca': equipo.marca or 'No especificada',
                    'Modelo': equipo.modelo or 'No especificado',
                    'Fecha Adquisición': equipo.fecha_adquisicion.strftime('%d/%m/%Y') if equipo.fecha_adquisicion else 'No especificada',
                    'Garantía': equipo.fecha_garantia_expiracion.strftime('%d/%m/%Y') if equipo.fecha_garantia_expiracion else 'No aplica',
                    'Días Garantía': dias_garantia if dias_garantia is not None else 'No aplica',
                    'Proveedor': equipo.proveedor.nombre if equipo.proveedor else 'No especificado'
                })
        
        logger.info(f"Reporte generado: {filepath}")
        
        # Notificar a los administradores
        mensaje = f"Reporte de estado de equipos generado: {filename}"
        await send_role_notifications("admin", mensaje)
        
        return str(filepath)


@register_task("generate_maintenance_report")
async def generate_maintenance_report(start_date: str, end_date: str) -> str:
    """
    Genera un reporte de mantenimientos en un período de tiempo.
    
    Args:
        start_date: Fecha de inicio en formato YYYY-MM-DD
        end_date: Fecha de fin en formato YYYY-MM-DD
        
    Returns:
        Ruta al archivo de reporte generado
    """
    logger.info(f"Generando reporte de mantenimientos del {start_date} al {end_date}")
    
    # Convertir fechas
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    # Nombre de archivo
    filename = f"mantenimientos_{start_date}_a_{end_date}.csv"
    filepath = REPORTS_DIR / filename
    
    async with async_session_factory() as session:
        # Obtener mantenimientos en el período
        stmt = select(Mantenimiento).where(
            Mantenimiento.fecha_mantenimiento.between(start, end)
        ).options(
            joinedload(Mantenimiento.equipo),
            joinedload(Mantenimiento.tipo_mantenimiento)
        ).order_by(Mantenimiento.fecha_mantenimiento)
        
        result = await session.execute(stmt)
        mantenimientos = result.unique().scalars().all()
        
        # Crear archivo CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'ID', 'Equipo', 'Tipo', 'Fecha', 'Estado', 'Técnico', 
                'Costo', 'Observaciones'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for mant in mantenimientos:
                writer.writerow({
                    'ID': str(mant.id),
                    'Equipo': mant.equipo.nombre if mant.equipo else 'Desconocido',
                    'Tipo': mant.tipo_mantenimiento.nombre if mant.tipo_mantenimiento else 'Desconocido',
                    'Fecha': mant.fecha_mantenimiento.strftime('%d/%m/%Y'),
                    'Estado': mant.estado,
                    'Técnico': mant.tecnico_responsable,
                    'Costo': f"{mant.costo:.2f}" if mant.costo else 'No especificado',
                    'Observaciones': mant.observaciones or 'No hay observaciones'
                })
        
        logger.info(f"Reporte generado: {filepath}")
        
        # Notificar a los supervisores
        mensaje = f"Reporte de mantenimientos del {start_date} al {end_date} generado"
        await send_role_notifications("supervisor", mensaje)
        
        return str(filepath)


@register_task("generate_movements_report")
async def generate_movements_report(days: int = 30) -> str:
    """
    Genera un reporte de movimientos de los últimos días.
    
    Args:
        days: Número de días hacia atrás para incluir en el reporte
        
    Returns:
        Ruta al archivo de reporte generado
    """
    logger.info(f"Generando reporte de movimientos de los últimos {days} días")
    
    # Calcular fecha de inicio
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    # Formato de fechas para el nombre del archivo
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    filename = f"movimientos_{start_str}_a_{end_str}.csv"
    filepath = REPORTS_DIR / filename
    
    async with async_session_factory() as session:
        # Obtener movimientos en el período
        stmt = select(Movimiento).where(
            Movimiento.fecha_hora.between(start_date, end_date)
        ).options(
            joinedload(Movimiento.equipo),
            joinedload(Movimiento.usuario)
        ).order_by(Movimiento.fecha_hora.desc())
        
        result = await session.execute(stmt)
        movimientos = result.unique().scalars().all()
        
        # Crear archivo CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'ID', 'Equipo', 'Tipo', 'Fecha', 'Usuario', 'Destino', 
                'Fecha Retorno', 'Estado', 'Observaciones'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for mov in movimientos:
                writer.writerow({
                    'ID': str(mov.id),
                    'Equipo': mov.equipo.nombre if mov.equipo else 'Desconocido',
                    'Tipo': mov.tipo_movimiento,
                    'Fecha': mov.fecha_hora.strftime('%d/%m/%Y %H:%M'),
                    'Usuario': mov.usuario.nombre_usuario if mov.usuario else 'Desconocido',
                    'Destino': mov.destino or 'No aplica',
                    'Fecha Retorno': mov.fecha_retorno.strftime('%d/%m/%Y %H:%M') if mov.fecha_retorno else 'Pendiente',
                    'Estado': mov.estado,
                    'Observaciones': mov.observaciones or 'No hay observaciones'
                })
        
        logger.info(f"Reporte generado: {filepath}")
        
        # Notificar a los supervisores
        mensaje = f"Reporte de movimientos de los últimos {days} días generado"
        await send_role_notifications("supervisor", mensaje)
        
        return str(filepath)
