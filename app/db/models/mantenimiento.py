from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship

from app.db.base import BaseModel, SearchableMixin

if TYPE_CHECKING:
    from app.db.models.equipos import Equipo


class TipoMantenimiento(BaseModel):
    """Modelo para los tipos de mantenimiento."""
    __tablename__ = "tipos_mantenimiento"
    
    nombre = Column(String, unique=True, nullable=False, index=True)
    descripcion = Column(Text, nullable=True)
    periodicidad_dias = Column(Integer, nullable=True)
    requiere_documentacion = Column(Boolean, default=False)
    
    # Relaciones
    mantenimientos: Mapped[list["Mantenimiento"]] = relationship(
        "Mantenimiento", 
        back_populates="tipo_mantenimiento"
    )
    
    def __repr__(self) -> str:
        return f"<TipoMantenimiento {self.nombre}>"


class Mantenimiento(BaseModel, SearchableMixin):
    """Modelo para registros de mantenimiento de equipos."""
    __tablename__ = "mantenimiento"
    
    equipo_id = Column(UUID(as_uuid=True), ForeignKey("equipos.id", ondelete="CASCADE"), nullable=False)
    tipo_mantenimiento_id = Column(UUID(as_uuid=True), ForeignKey("tipos_mantenimiento.id"), nullable=False)
    fecha_mantenimiento = Column(DateTime(timezone=True), server_default=func.now())
    fecha_proximo_mantenimiento = Column(DateTime(timezone=True), nullable=True)
    costo = Column(Numeric(10, 2), nullable=True)
    tecnico_responsable = Column(String, nullable=False)
    estado = Column(String, default="programado", nullable=False)
    observaciones = Column(Text, nullable=True)
    
    # Restricciones
    __table_args__ = (
        CheckConstraint(
            "estado IN ('programado', 'en_proceso', 'completado', 'cancelado')",
            name="check_estado_mantenimiento"
        ),
        CheckConstraint(
            "costo IS NULL OR costo >= 0",
            name="check_costo_positivo"
        ),
    )
    
    # Relaciones
    equipo: Mapped["Equipo"] = relationship("Equipo", back_populates="mantenimientos")
    tipo_mantenimiento: Mapped[TipoMantenimiento] = relationship(
        "TipoMantenimiento", 
        back_populates="mantenimientos"
    )
    
    def __repr__(self) -> str:
        return f"<Mantenimiento {self.tipo_mantenimiento.nombre if self.tipo_mantenimiento else 'desconocido'} para {self.equipo_id}>"
    
    def actualizar_estado(self, nuevo_estado: str) -> None:
        """
        Actualiza el estado del mantenimiento.
        
        Args:
            nuevo_estado: Nuevo estado (programado, en_proceso, completado, cancelado)
        """
        estados_validos = ["programado", "en_proceso", "completado", "cancelado"]
        if nuevo_estado not in estados_validos:
            raise ValueError(f"Estado inválido. Debe ser uno de: {', '.join(estados_validos)}")
            
        # Si se completa el mantenimiento, calcular próxima fecha
        if nuevo_estado == "completado" and self.tipo_mantenimiento and self.tipo_mantenimiento.periodicidad_dias:
            self.fecha_proximo_mantenimiento = datetime.now(timezone.utc) + timedelta(
                days=self.tipo_mantenimiento.periodicidad_dias
            )
            
        self.estado = nuevo_estado
    
    def cancelar(self) -> None:
        """Cancela el mantenimiento."""
        self.actualizar_estado("cancelado")
    
    def iniciar(self) -> None:
        """Inicia el mantenimiento."""
        self.actualizar_estado("en_proceso")
    
    def completar(self, observaciones: Optional[str] = None, costo: Optional[Decimal] = None) -> None:
        """
        Marca el mantenimiento como completado.
        
        Args:
            observaciones: Observaciones sobre el mantenimiento
            costo: Costo del mantenimiento
        """
        if observaciones:
            self.observaciones = observaciones
        if costo is not None:
            self.costo = costo
            
        self.actualizar_estado("completado")
    
    def esta_vencido(self) -> bool:
        """
        Verifica si el mantenimiento está vencido.
        
        Returns:
            True si está vencido, False en caso contrario
        """
        if self.estado in ["completado", "cancelado"]:
            return False
            
        return datetime.now(timezone.utc) > self.fecha_mantenimiento
