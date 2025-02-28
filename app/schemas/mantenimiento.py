from datetime import datetime
from decimal import Decimal
from typing import Optional
import uuid

from pydantic import BaseModel, Field, validator


class TipoMantenimientoBase(BaseModel):
    """Esquema base para tipos de mantenimiento."""
    nombre: str = Field(..., min_length=3, max_length=50)
    descripcion: Optional[str] = None
    periodicidad_dias: Optional[int] = Field(None, gt=0)
    requiere_documentacion: bool = False


class TipoMantenimientoCreate(TipoMantenimientoBase):
    """Esquema para crear un tipo de mantenimiento."""
    pass


class TipoMantenimientoUpdate(BaseModel):
    """Esquema para actualizar un tipo de mantenimiento."""
    nombre: Optional[str] = Field(None, min_length=3, max_length=50)
    descripcion: Optional[str] = None
    periodicidad_dias: Optional[int] = Field(None, gt=0)
    requiere_documentacion: Optional[bool] = None


class TipoMantenimiento(TipoMantenimientoBase):
    """Esquema para representar un tipo de mantenimiento."""
    id: uuid.UUID
    
    class Config:
        from_attributes = True


class MantenimientoBase(BaseModel):
    """Esquema base para mantenimientos."""
    equipo_id: uuid.UUID
    tipo_mantenimiento_id: uuid.UUID
    tecnico_responsable: str = Field(..., min_length=3, max_length=100)
    fecha_mantenimiento: Optional[datetime] = None
    costo: Optional[Decimal] = Field(None, ge=0)
    observaciones: Optional[str] = None


class MantenimientoCreate(MantenimientoBase):
    """Esquema para crear un mantenimiento."""
    pass


class MantenimientoUpdate(BaseModel):
    """Esquema para actualizar un mantenimiento."""
    tipo_mantenimiento_id: Optional[uuid.UUID] = None
    tecnico_responsable: Optional[str] = Field(None, min_length=3, max_length=100)
    fecha_mantenimiento: Optional[datetime] = None
    costo: Optional[Decimal] = Field(None, ge=0)
    observaciones: Optional[str] = None
    estado: Optional[str] = Field(None, pattern=r'^(programado|en_proceso|completado|cancelado)$')


class MantenimientoEstado(BaseModel):
    """Esquema para actualizar el estado de un mantenimiento."""
    estado: str = Field(..., pattern=r'^(programado|en_proceso|completado|cancelado)$')
    observaciones: Optional[str] = None
    costo: Optional[Decimal] = Field(None, ge=0)


class Mantenimiento(MantenimientoBase):
    """Esquema para representar un mantenimiento."""
    id: uuid.UUID
    fecha_proximo_mantenimiento: Optional[datetime] = None
    estado: str
    
    class Config:
        from_attributes = True


class MantenimientoConDetalles(Mantenimiento):
    """Esquema para representar un mantenimiento con detalles adicionales."""
    equipo_nombre: str
    equipo_numero_serie: str
    tipo_mantenimiento_nombre: str
    vencido: bool = False
    dias_para_proximo: Optional[int] = None
    
    class Config:
        from_attributes = True
