from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, List
import uuid

from pydantic import BaseModel, Field, field_validator, model_validator


class ProveedorBase(BaseModel):
    """Esquema base para proveedores."""
    nombre: str = Field(..., min_length=3, max_length=100)
    descripcion: Optional[str] = None
    contacto: Optional[str] = None


class ProveedorCreate(ProveedorBase):
    """Esquema para crear un proveedor."""
    pass


class ProveedorUpdate(BaseModel):
    """Esquema para actualizar un proveedor."""
    nombre: Optional[str] = Field(None, min_length=3, max_length=100)
    descripcion: Optional[str] = None
    contacto: Optional[str] = None


class Proveedor(ProveedorBase):
    """Esquema para representar un proveedor."""
    id: uuid.UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class EstadoEquipoBase(BaseModel):
    """Esquema base para estados de equipo."""
    nombre: str = Field(..., min_length=3, max_length=50)
    descripcion: Optional[str] = None
    permite_movimientos: bool = True
    requiere_autorizacion: bool = False


class EstadoEquipoCreate(EstadoEquipoBase):
    """Esquema para crear un estado de equipo."""
    pass


class EstadoEquipoUpdate(BaseModel):
    """Esquema para actualizar un estado de equipo."""
    nombre: Optional[str] = Field(None, min_length=3, max_length=50)
    descripcion: Optional[str] = None
    permite_movimientos: Optional[bool] = None
    requiere_autorizacion: Optional[bool] = None


class EstadoEquipo(EstadoEquipoBase):
    """Esquema para representar un estado de equipo."""
    id: uuid.UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class EquipoBase(BaseModel):
    """Esquema base para equipos."""
    nombre: str = Field(..., min_length=3, max_length=100)
    numero_serie: str = Field(..., pattern=r'^[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+$')
    estado_id: uuid.UUID
    ubicacion_actual: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    fecha_adquisicion: Optional[date] = None
    fecha_garantia_expiracion: Optional[date] = None
    valor_adquisicion: Optional[Decimal] = Field(None, ge=0)
    proveedor_id: Optional[uuid.UUID] = None
    notas: Optional[str] = None


class EquipoCreate(EquipoBase):
    """Esquema para crear un equipo."""
    @field_validator('fecha_adquisicion')
    @classmethod
    def validate_fecha_adquisicion(cls, v: Optional[date]) -> Optional[date]:
        """Validar que la fecha de adquisición no sea futura."""
        if v and v > date.today():
            raise ValueError('La fecha de adquisición no puede ser futura')
        return v
    
    @model_validator(mode='after')
    def validate_dates(self) -> 'EquipoCreate':
        """Validar que la fecha de garantía sea posterior a la adquisición."""
        if (self.fecha_adquisicion and self.fecha_garantia_expiracion and 
            self.fecha_garantia_expiracion < self.fecha_adquisicion):
            raise ValueError('La fecha de garantía debe ser posterior a la fecha de adquisición')
        return self


class EquipoUpdate(BaseModel):
    """Esquema para actualizar un equipo."""
    nombre: Optional[str] = Field(None, min_length=3, max_length=100)
    numero_serie: Optional[str] = Field(None, pattern=r'^[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+$')
    estado_id: Optional[uuid.UUID] = None
    ubicacion_actual: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    fecha_adquisicion: Optional[date] = None
    fecha_garantia_expiracion: Optional[date] = None
    valor_adquisicion: Optional[Decimal] = Field(None, ge=0)
    proveedor_id: Optional[uuid.UUID] = None
    notas: Optional[str] = None
    
    @field_validator('fecha_adquisicion')
    @classmethod
    def validate_fecha_adquisicion(cls, v: Optional[date]) -> Optional[date]:
        """Validar que la fecha de adquisición no sea futura."""
        if v and v > date.today():
            raise ValueError('La fecha de adquisición no puede ser futura')
        return v


class EquipoBusqueda(BaseModel):
    """Esquema para resultados de búsqueda de equipos."""
    id: uuid.UUID
    nombre: str
    numero_serie: str
    marca: Optional[str] = None
    modelo: Optional[str] = None
    relevancia: float
    
    class Config:
        from_attributes = True


class Equipo(EquipoBase):
    """Esquema para representar un equipo."""
    id: uuid.UUID
    fecha_ultima_actualizacion: datetime
    created_at: datetime
    updated_at: datetime
    
    # Relaciones
    estado: Optional[EstadoEquipo] = None
    proveedor: Optional[Proveedor] = None
    
    class Config:
        from_attributes = True


class EquipoConRelaciones(Equipo):
    """Esquema para representar un equipo con todas sus relaciones."""
    movimientos_count: int = 0
    documentos_count: int = 0
    mantenimientos_count: int = 0
    dias_garantia_restantes: Optional[int] = None
    estado_garantia: str = "Sin garantía"
    
    class Config:
        from_attributes = True


class TipoDocumentoBase(BaseModel):
    """Esquema base para tipos de documento."""
    nombre: str = Field(..., min_length=3, max_length=50)
    descripcion: Optional[str] = None
    requiere_verificacion: bool = False
    formato_permitido: List[str] = []


class TipoDocumentoCreate(TipoDocumentoBase):
    """Esquema para crear un tipo de documento."""
    pass


class TipoDocumentoUpdate(BaseModel):
    """Esquema para actualizar un tipo de documento."""
    nombre: Optional[str] = Field(None, min_length=3, max_length=50)
    descripcion: Optional[str] = None
    requiere_verificacion: Optional[bool] = None
    formato_permitido: Optional[List[str]] = None


class TipoDocumento(TipoDocumentoBase):
    """Esquema para representar un tipo de documento."""
    id: uuid.UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class DocumentacionBase(BaseModel):
    """Esquema base para documentación."""
    equipo_id: uuid.UUID
    tipo_documento_id: uuid.UUID
    titulo: str = Field(..., min_length=3, max_length=100)
    descripcion: Optional[str] = None
    enlace: str


class DocumentacionCreate(DocumentacionBase):
    """Esquema para crear documentación."""
    # El campo subido_por se tomará del usuario autenticado
    pass


class DocumentacionUpdate(BaseModel):
    """Esquema para actualizar documentación."""
    tipo_documento_id: Optional[uuid.UUID] = None
    titulo: Optional[str] = Field(None, min_length=3, max_length=100)
    descripcion: Optional[str] = None
    enlace: Optional[str] = None


class DocumentacionVerificar(BaseModel):
    """Esquema para verificar documentación."""
    estado: str = Field(..., pattern=r'^(verificado|rechazado)$')


class Documentacion(DocumentacionBase):
    """Esquema para representar documentación."""
    id: uuid.UUID
    fecha_subida: datetime
    subido_por: Optional[uuid.UUID] = None
    estado: str
    verificado_por: Optional[uuid.UUID] = None
    fecha_verificacion: Optional[datetime] = None
    
    # Relaciones opcionales
    tipo_documento: Optional[TipoDocumento] = None
    
    class Config:
        from_attributes = True


class DocumentacionConUsuarios(Documentacion):
    """Esquema para representar documentación con información de usuarios."""
    subido_por_nombre: Optional[str] = None
    verificado_por_nombre: Optional[str] = None
    
    class Config:
        from_attributes = True
