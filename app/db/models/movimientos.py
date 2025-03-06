from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.db.models.equipos import Equipo
    from app.db.models.usuarios import Usuario


class Movimiento(BaseModel):
    """Modelo para los movimientos de equipos (salidas y entradas)."""
    __tablename__ = "movimientos"
    
    equipo_id = Column(UUID(as_uuid=True), ForeignKey("equipos.id", ondelete="CASCADE"), nullable=False)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    tipo_movimiento = Column(String, nullable=False)
    fecha_hora = Column(DateTime(timezone=True), server_default=func.now())
    fecha_prevista_retorno = Column(DateTime(timezone=True), nullable=True)
    fecha_retorno = Column(DateTime(timezone=True), nullable=True)
    destino = Column(String, nullable=True)
    proposito = Column(Text, nullable=True)
    autorizado_por = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    recibido_por = Column(String, nullable=True)
    observaciones = Column(Text, nullable=True)
    estado = Column(String, default="pendiente", nullable=False)
    
    # Restricciones adicionales (las mismas que en la BD)
    __table_args__ = (
        CheckConstraint(
            "(tipo_movimiento = 'salida' AND destino IS NOT NULL) OR (tipo_movimiento = 'entrada')",
            name="check_destino_salida"
        ),
        CheckConstraint(
            "tipo_movimiento IN ('salida', 'entrada')",
            name="check_tipo_movimiento"
        ),
        CheckConstraint(
            "estado IN ('pendiente', 'en_proceso', 'completado', 'cancelado')",
            name="check_estado_movimiento"
        ),
    )
    
    # Relaciones
    equipo: Mapped["Equipo"] = relationship("Equipo", back_populates="movimientos")
    usuario: Mapped[Optional["Usuario"]] = relationship(
        "Usuario", 
        foreign_keys=[usuario_id],
        back_populates="movimientos"
    )
    autorizado_por_usuario: Mapped[Optional["Usuario"]] = relationship(
        "Usuario", 
        foreign_keys=[autorizado_por],
        back_populates="movimientos_autorizados"
    )
    
    def __repr__(self) -> str:
        tipo = "Salida" if self.tipo_movimiento == "salida" else "Entrada"
        return f"<{tipo} de {self.equipo_id}>"
    
    def actualizar_estado(self, nuevo_estado: str) -> None:
        """
        Actualiza el estado del movimiento.
        
        Args:
            nuevo_estado: Nuevo estado (pendiente, en_proceso, completado, cancelado)
        """
        estados_validos = ["pendiente", "en_proceso", "completado", "cancelado"]
        if nuevo_estado not in estados_validos:
            raise ValueError(f"Estado inválido. Debe ser uno de: {', '.join(estados_validos)}")
            
        self.estado = nuevo_estado
    
    def registrar_retorno(self, recibido_por: Optional[str] = None) -> None:
        """
        Registra el retorno del equipo.
        
        Args:
            recibido_por: Persona que recibe el equipo
        """
        self.fecha_retorno = datetime.now(timezone.utc)
        if recibido_por:
            self.recibido_por = recibido_por
        self.actualizar_estado("completado")
    
    def cancelar(self) -> None:
        """Cancela el movimiento."""
        self.actualizar_estado("cancelado")
    
    def esta_en_tiempo(self) -> bool:
        """
        Verifica si el movimiento está dentro del tiempo previsto de retorno.
        
        Returns:
            True si está en tiempo o no tiene fecha prevista, False si está atrasado
        """
        if not self.fecha_prevista_retorno:
            return True
            
        return datetime.now(timezone.utc) <= self.fecha_prevista_retorno
