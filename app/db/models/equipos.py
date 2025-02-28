from datetime import date, datetime, timezone
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship

from app.db.base import AuditableMixin, BaseModel, SearchableMixin

if TYPE_CHECKING:
    from app.db.models.mantenimiento import Mantenimiento
    from app.db.models.movimientos import Movimiento
    from app.db.models.usuarios import Usuario


class EstadoEquipo(BaseModel):
    """Modelo para los estados de equipos."""
    __tablename__ = "estados_equipo"
    
    nombre = Column(String, unique=True, nullable=False, index=True)
    descripcion = Column(Text, nullable=True)
    permite_movimientos = Column(Boolean, default=True)
    requiere_autorizacion = Column(Boolean, default=False)
    
    # Relaciones
    equipos: Mapped[List["Equipo"]] = relationship("Equipo", back_populates="estado")
    
    def __repr__(self) -> str:
        return f"<EstadoEquipo {self.nombre}>"


class Proveedor(BaseModel, AuditableMixin):
    """Modelo para los proveedores de equipos."""
    __tablename__ = "proveedores"
    
    nombre = Column(String, unique=True, nullable=False, index=True)
    descripcion = Column(Text, nullable=True)
    contacto = Column(Text, nullable=True)
    
    # Relaciones
    equipos: Mapped[List["Equipo"]] = relationship("Equipo", back_populates="proveedor")
    
    def __repr__(self) -> str:
        return f"<Proveedor {self.nombre}>"


class Equipo(BaseModel, AuditableMixin, SearchableMixin):
    """Modelo para los equipos."""
    __tablename__ = "equipos"
    
    nombre = Column(String, nullable=False, index=True)
    numero_serie = Column(String, unique=True, nullable=False, index=True)
    estado_id = Column(UUID(as_uuid=True), ForeignKey("estados_equipo.id"), nullable=False)
    ubicacion_actual = Column(String, nullable=True)
    marca = Column(String, nullable=True)
    modelo = Column(String, nullable=True)
    fecha_adquisicion = Column(Date, nullable=True)
    fecha_garantia_expiracion = Column(Date, nullable=True)
    valor_adquisicion = Column(Numeric(10, 2), nullable=True)
    proveedor_id = Column(UUID(as_uuid=True), ForeignKey("proveedores.id"), nullable=True)
    notas = Column(Text, nullable=True)
    fecha_ultima_actualizacion = Column(DateTime(timezone=True), 
                                       server_default=func.now(), 
                                       onupdate=func.now())
    
    # Validaciones como check constraints se manejan en la BD
    # En el ORM añadimos validaciones a nivel de aplicación
    
    # Relaciones
    estado: Mapped[EstadoEquipo] = relationship("EstadoEquipo", back_populates="equipos")
    proveedor: Mapped[Optional[Proveedor]] = relationship("Proveedor", back_populates="equipos")
    movimientos: Mapped[List["Movimiento"]] = relationship("Movimiento", back_populates="equipo")
    documentacion: Mapped[List["Documentacion"]] = relationship("Documentacion", back_populates="equipo")
    mantenimientos: Mapped[List["Mantenimiento"]] = relationship("Mantenimiento", back_populates="equipo")
    
    def __repr__(self) -> str:
        return f"<Equipo {self.nombre} ({self.numero_serie})>"
    
    def esta_disponible(self) -> bool:
        """Verifica si el equipo está disponible para movimientos."""
        return self.estado.permite_movimientos if self.estado else False
    
    def requiere_autorizacion(self) -> bool:
        """Verifica si el equipo requiere autorización para movimientos."""
        return self.estado.requiere_autorizacion if self.estado else False
    
    def actualizar_ubicacion(self, nueva_ubicacion: str) -> None:
        """Actualiza la ubicación del equipo."""
        self.ubicacion_actual = nueva_ubicacion
        self.fecha_ultima_actualizacion = datetime.now(timezone.utc)
    
    def calcular_dias_garantia(self) -> Optional[int]:
        """Calcula los días restantes de garantía."""
        if not self.fecha_garantia_expiracion:
            return None
        
        dias = (self.fecha_garantia_expiracion - date.today()).days
        return max(0, dias)
    
    def verificar_garantia_activa(self) -> bool:
        """Verifica si la garantía del equipo está activa."""
        if not self.fecha_garantia_expiracion:
            return False
            
        return self.fecha_garantia_expiracion >= date.today()


class TipoDocumento(BaseModel):
    """Modelo para los tipos de documentos asociados a equipos."""
    __tablename__ = "tipos_documento"
    
    nombre = Column(String, unique=True, nullable=False, index=True)
    descripcion = Column(Text, nullable=True)
    requiere_verificacion = Column(Boolean, default=False)
    formato_permitido = Column(String, nullable=True)  # Array en PG, aquí como string separado por comas
    
    # Relaciones
    documentos: Mapped[List["Documentacion"]] = relationship("Documentacion", back_populates="tipo_documento")
    
    def __repr__(self) -> str:
        return f"<TipoDocumento {self.nombre}>"
    
    def get_formatos_permitidos(self) -> List[str]:
        """Obtiene la lista de formatos permitidos."""
        if not self.formato_permitido:
            return []
        return [f.strip() for f in self.formato_permitido.split(',')]


class Documentacion(BaseModel, SearchableMixin):
    """Modelo para documentos asociados a equipos."""
    __tablename__ = "documentacion"
    
    equipo_id = Column(UUID(as_uuid=True), ForeignKey("equipos.id", ondelete="CASCADE"), nullable=False)
    tipo_documento_id = Column(UUID(as_uuid=True), ForeignKey("tipos_documento.id"), nullable=False)
    titulo = Column(String, nullable=False)
    descripcion = Column(Text, nullable=True)
    enlace = Column(String, nullable=False)  # URL al documento
    fecha_subida = Column(DateTime(timezone=True), server_default=func.now())
    subido_por = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    estado = Column(String, nullable=False, default="pendiente")  # pendiente, verificado, rechazado
    verificado_por = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    fecha_verificacion = Column(DateTime(timezone=True), nullable=True)
    
    # Relaciones
    equipo: Mapped[Equipo] = relationship("Equipo", back_populates="documentacion")
    tipo_documento: Mapped[TipoDocumento] = relationship("TipoDocumento", back_populates="documentos")
    subido_por_usuario: Mapped[Optional["Usuario"]] = relationship(
        "Usuario", 
        foreign_keys=[subido_por],
        back_populates="documentos_subidos"
    )
    verificado_por_usuario: Mapped[Optional["Usuario"]] = relationship(
        "Usuario", 
        foreign_keys=[verificado_por],
        back_populates="documentos_verificados"
    )
    
    def __repr__(self) -> str:
        return f"<Documentacion {self.titulo} para {self.equipo_id}>"
    
    def verificar(self, usuario_id: UUID) -> None:
        """Marca el documento como verificado."""
        self.estado = "verificado"
        self.verificado_por = usuario_id
        self.fecha_verificacion = datetime.now(timezone.utc)
    
    def rechazar(self, usuario_id: UUID) -> None:
        """Marca el documento como rechazado."""
        self.estado = "rechazado"
        self.verificado_por = usuario_id
        self.fecha_verificacion = datetime.now(timezone.utc)
