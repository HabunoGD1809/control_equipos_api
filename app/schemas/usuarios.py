from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import BaseModel, EmailStr, Field, field_validator


class PermisoBase(BaseModel):
    """Esquema base para permisos."""
    nombre: str = Field(..., min_length=3, max_length=50)
    descripcion: Optional[str] = None


class PermisoCreate(PermisoBase):
    """Esquema para crear un permiso."""
    pass


class PermisoUpdate(PermisoBase):
    """Esquema para actualizar un permiso."""
    nombre: Optional[str] = Field(None, min_length=3, max_length=50)


class Permiso(PermisoBase):
    """Esquema para representar un permiso."""
    id: uuid.UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class RolBase(BaseModel):
    """Esquema base para roles."""
    nombre: str = Field(..., min_length=3, max_length=50)
    descripcion: Optional[str] = None


class RolCreate(RolBase):
    """Esquema para crear un rol."""
    permisos_ids: Optional[List[uuid.UUID]] = None


class RolUpdate(BaseModel):
    """Esquema para actualizar un rol."""
    nombre: Optional[str] = Field(None, min_length=3, max_length=50)
    descripcion: Optional[str] = None
    permisos_ids: Optional[List[uuid.UUID]] = None


class Rol(RolBase):
    """Esquema para representar un rol."""
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    permisos: List[Permiso] = []
    
    class Config:
        from_attributes = True


class UsuarioBase(BaseModel):
    """Esquema base para usuarios."""
    nombre_usuario: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None


class UsuarioCreate(UsuarioBase):
    """Esquema para crear un usuario."""
    contrasena: str = Field(..., min_length=8)
    rol_id: uuid.UUID
    requiere_cambio_contrasena: bool = True
    
    @field_validator('contrasena')
    @classmethod
    def password_must_be_strong(cls, v: str) -> str:
        """Validar que la contraseña sea fuerte."""
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not any(c.isupper() for c in v):
            raise ValueError('La contraseña debe contener al menos una letra mayúscula')
        if not any(c.islower() for c in v):
            raise ValueError('La contraseña debe contener al menos una letra minúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v


class UsuarioUpdate(BaseModel):
    """Esquema para actualizar un usuario."""
    nombre_usuario: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    rol_id: Optional[uuid.UUID] = None
    bloqueado: Optional[bool] = None
    requiere_cambio_contrasena: Optional[bool] = None


class UsuarioChangePassword(BaseModel):
    """Esquema para cambiar la contraseña de un usuario."""
    contrasena_actual: str
    nueva_contrasena: str = Field(..., min_length=8)
    confirmar_contrasena: str
    
    @field_validator('confirmar_contrasena')
    @classmethod
    def passwords_match(cls, v: str, values: dict) -> str:
        """Validar que las contraseñas coincidan."""
        if 'nueva_contrasena' in values and v != values['nueva_contrasena']:
            raise ValueError('Las contraseñas no coinciden')
        return v
    
    @field_validator('nueva_contrasena')
    @classmethod
    def password_must_be_strong(cls, v: str, values: dict) -> str:
        """Validar que la contraseña sea fuerte."""
        if 'contrasena_actual' in values and v == values['contrasena_actual']:
            raise ValueError('La nueva contraseña debe ser diferente a la actual')
        
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not any(c.isupper() for c in v):
            raise ValueError('La contraseña debe contener al menos una letra mayúscula')
        if not any(c.islower() for c in v):
            raise ValueError('La contraseña debe contener al menos una letra minúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v


class Usuario(UsuarioBase):
    """Esquema para representar un usuario."""
    id: uuid.UUID
    rol_id: uuid.UUID
    bloqueado: bool
    ultimo_login: Optional[datetime] = None
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    requiere_cambio_contrasena: bool
    rol: Optional[Rol] = None
    
    class Config:
        from_attributes = True


class UsuarioInDB(Usuario):
    """Esquema para representar un usuario con datos sensibles (solo para uso interno)."""
    contrasena: str
    intentos_fallidos: int
    token_temporal: Optional[uuid.UUID] = None
    token_expiracion: Optional[datetime] = None


class NotificacionBase(BaseModel):
    """Esquema base para notificaciones."""
    mensaje: str
    usuario_id: uuid.UUID


class NotificacionCreate(NotificacionBase):
    """Esquema para crear una notificación."""
    pass


class Notificacion(NotificacionBase):
    """Esquema para representar una notificación."""
    id: uuid.UUID
    leido: bool
    fecha_creacion: datetime
    fecha_leido: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class LoginLogBase(BaseModel):
    """Esquema base para registros de login."""
    usuario_id: Optional[uuid.UUID] = None
    exito: bool
    ip_origen: Optional[str] = None


class LoginLogCreate(LoginLogBase):
    """Esquema para crear un registro de login."""
    pass


class LoginLog(LoginLogBase):
    """Esquema para representar un registro de login."""
    id: uuid.UUID
    intento: datetime
    
    class Config:
        from_attributes = True
