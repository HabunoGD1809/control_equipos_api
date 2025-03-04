import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship

from app.db.base import AuditableMixin, BaseModel
from app.db.session import Base

if TYPE_CHECKING:
    from app.db.models.movimientos import Movimiento
    from app.db.models.equipos import Documentacion


# Tabla de relación entre roles y permisos
roles_permisos = Table(
    'roles_permisos',
    Base.metadata,
    Column('rol_id', UUID(as_uuid=True), ForeignKey('roles.id', ondelete="CASCADE"), primary_key=True),
    Column('permiso_id', UUID(as_uuid=True), ForeignKey('permisos.id', ondelete="CASCADE"), primary_key=True),
    Column('otorgado_por', UUID(as_uuid=True), nullable=True),
    Column('fecha_otorgamiento', DateTime(timezone=True), default=func.now()),
)


class Permiso(BaseModel):
    """Modelo para los permisos del sistema."""
    __tablename__ = "permisos"
    
    nombre = Column(String, unique=True, nullable=False, index=True)
    descripcion = Column(Text, nullable=True)
    
    # Relaciones
    roles: Mapped[List["Rol"]] = relationship(
        "Rol", 
        secondary=roles_permisos, 
        back_populates="permisos"
    )
    
    def __repr__(self) -> str:
        return f"<Permiso {self.nombre}>"


class Rol(BaseModel, AuditableMixin):
    """Modelo para los roles de usuario."""
    __tablename__ = "roles"
    
    nombre = Column(String, unique=True, nullable=False, index=True)
    descripcion = Column(Text, nullable=True)
    
    # Relaciones
    permisos: Mapped[List[Permiso]] = relationship(
        "Permiso", 
        secondary=roles_permisos, 
        back_populates="roles"
    )
    usuarios: Mapped[List["Usuario"]] = relationship(
        "Usuario", 
        back_populates="rol"
    )
    
    def __repr__(self) -> str:
        return f"<Rol {self.nombre}>"


class Usuario(BaseModel, AuditableMixin):
    """Modelo para los usuarios del sistema."""
    __tablename__ = "usuarios"
    
    nombre_usuario = Column(String, unique=True, nullable=False, index=True)
    contrasena = Column(String, nullable=False)
    rol_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    email = Column(String, unique=True, nullable=True, index=True)
    token_temporal = Column(UUID(as_uuid=True), nullable=True)
    token_expiracion = Column(DateTime(timezone=True), nullable=True)
    intentos_fallidos = Column(Integer, default=0)
    bloqueado = Column(Boolean, default=False)
    ultimo_login = Column(DateTime(timezone=True), nullable=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=True), server_default=func.now(),
                                onupdate=func.now())
    requiere_cambio_contrasena = Column(Boolean, default=True)
    
    # Relaciones
    rol: Mapped[Rol] = relationship("Rol", back_populates="usuarios")
    movimientos: Mapped[List["Movimiento"]] = relationship(
        "Movimiento", 
        back_populates="usuario",
        foreign_keys="[Movimiento.usuario_id]"
    )
    movimientos_autorizados: Mapped[List["Movimiento"]] = relationship(
        "Movimiento", 
        back_populates="autorizado_por_usuario",
        foreign_keys="[Movimiento.autorizado_por]"
    )
    documentos_subidos: Mapped[List["Documentacion"]] = relationship(
        "Documentacion", 
        back_populates="subido_por_usuario",
        foreign_keys="[Documentacion.subido_por]"
    )
    documentos_verificados: Mapped[List["Documentacion"]] = relationship(
        "Documentacion", 
        back_populates="verificado_por_usuario",
        foreign_keys="[Documentacion.verificado_por]"
    )
    notificaciones: Mapped[List["Notificacion"]] = relationship(
        "Notificacion", 
        back_populates="usuario"
    )
    login_logs: Mapped[List["LoginLog"]] = relationship(
        "LoginLog", 
        back_populates="usuario"
    )
    
    def __repr__(self) -> str:
        return f"<Usuario {self.nombre_usuario}>"
    
    def registrar_intento_fallido(self) -> None:
        """Registra un intento fallido de inicio de sesión."""
        self.intentos_fallidos += 1
        if self.intentos_fallidos >= 5:  # Umbral para bloqueo
            self.bloqueado = True
    
    def reset_intentos_fallidos(self) -> None:
        """Reinicia el contador de intentos fallidos."""
        self.intentos_fallidos = 0
    
    def registrar_login(self) -> None:
        """Registra un login exitoso."""
        self.ultimo_login = datetime.now(timezone.utc)
        self.reset_intentos_fallidos()
    
    def generar_token_temporal(self) -> uuid.UUID:
        """Genera un token temporal para recuperación de contraseña."""
        self.token_temporal = uuid.uuid4()
        self.token_expiracion = datetime.now(timezone.utc) + timedelta(hours=24)
        return self.token_temporal
    
    def validar_token_temporal(self, token: uuid.UUID) -> bool:
        """Valida un token temporal para cambio de contraseña."""
        if (
            self.token_temporal == token and 
            self.token_expiracion and 
            self.token_expiracion > datetime.now(timezone.utc)
        ):
            return True
        return False
    
    def limpiar_token_temporal(self) -> None:
        """Limpia el token temporal después de su uso."""
        self.token_temporal = None
        self.token_expiracion = None


class LoginLog(BaseModel):
    """Modelo para registrar intentos de inicio de sesión."""
    __tablename__ = "login_logs"
    
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    intento = Column(DateTime(timezone=True), server_default=func.now())
    exito = Column(Boolean)
    ip_origen = Column(String, nullable=True)
    
    # Relaciones
    usuario: Mapped[Optional[Usuario]] = relationship("Usuario", back_populates="login_logs")
    
    def __repr__(self) -> str:
        return f"<LoginLog {'exitoso' if self.exito else 'fallido'} para {self.usuario_id}>"


class Notificacion(BaseModel):
    """Modelo para notificaciones internas del sistema."""
    __tablename__ = "notificaciones"
    
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    mensaje = Column(Text, nullable=False)
    leido = Column(Boolean, default=False)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_leido = Column(DateTime(timezone=True), nullable=True)
    
    # Relaciones
    usuario: Mapped[Usuario] = relationship("Usuario", back_populates="notificaciones")
    
    def __repr__(self) -> str:
        return f"<Notificacion para {self.usuario_id}>"
    
    def marcar_como_leida(self) -> None:
        """Marca la notificación como leída."""
        self.leido = True
        self.fecha_leido = datetime.now(timezone.utc)
