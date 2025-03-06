from datetime import datetime, timezone
from typing import Optional
import uuid

from pydantic import BaseModel, Field, field_validator, model_validator


class MovimientoBase(BaseModel):
    """Esquema base para movimientos de equipos."""
    equipo_id: uuid.UUID
    tipo_movimiento: str = Field(..., pattern=r'^(salida|entrada)$')
    fecha_prevista_retorno: Optional[datetime] = None
    destino: Optional[str] = None
    proposito: Optional[str] = None
    recibido_por: Optional[str] = None
    observaciones: Optional[str] = None


class MovimientoCreate(MovimientoBase):
    """Esquema para crear un movimiento."""
    @field_validator('destino')
    @classmethod
    def validate_destino_salida(cls, v: Optional[str], values: dict) -> Optional[str]:
        """Validar que el destino sea obligatorio para salidas."""
        if values.get('tipo_movimiento') == 'salida' and not v:
            raise ValueError('El destino es obligatorio para movimientos de salida')
        return v
    
    @field_validator('fecha_prevista_retorno')
    @classmethod
    def validate_fecha_prevista_retorno(cls, v: Optional[datetime], values: dict) -> Optional[datetime]:
        """Validar que la fecha prevista sea futura para salidas."""
        if values.get('tipo_movimiento') == 'salida' and v and v <= datetime.now(timezone.utc):
            raise ValueError('La fecha prevista de retorno debe ser futura')
        return v


class MovimientoUpdate(BaseModel):
    """Esquema para actualizar un movimiento."""
    fecha_prevista_retorno: Optional[datetime] = None
    destino: Optional[str] = None
    proposito: Optional[str] = None
    recibido_por: Optional[str] = None
    observaciones: Optional[str] = None
    fecha_retorno: Optional[datetime] = None
    estado: Optional[str] = Field(None, pattern=r'^(pendiente|en_proceso|completado|cancelado)$')
    
    @field_validator('fecha_retorno')
    @classmethod
    def validate_fecha_retorno(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Validar que la fecha de retorno no sea futura."""
        if v and v > datetime.now(timezone.utc):
            raise ValueError('La fecha de retorno no puede ser futura')
        return v


class MovimientoAutorizar(BaseModel):
    """Esquema para autorizar un movimiento."""
    autorizado: bool = True
    observaciones: Optional[str] = None


class MovimientoRetorno(BaseModel):
    """Esquema para registrar el retorno de un equipo."""
    recibido_por: str
    observaciones: Optional[str] = None


class MovimientoCancelar(BaseModel):
    """Esquema para cancelar un movimiento."""
    motivo: str = Field(..., min_length=5)


class Movimiento(MovimientoBase):
    """Esquema para representar un movimiento."""
    id: uuid.UUID
    usuario_id: Optional[uuid.UUID] = None
    fecha_hora: datetime
    fecha_retorno: Optional[datetime] = None
    autorizado_por: Optional[uuid.UUID] = None
    estado: str
    
    class Config:
        from_attributes = True


class MovimientoConDetalles(Movimiento):
    """Esquema para representar un movimiento con detalles adicionales."""
    equipo_nombre: str
    equipo_numero_serie: str
    usuario_nombre: Optional[str] = None
    autorizado_por_nombre: Optional[str] = None
    estado_equipo: str
    retrasado: bool = False
    dias_restantes: Optional[int] = None
    
    class Config:
        from_attributes = True
