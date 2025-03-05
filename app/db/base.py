import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr

from app.db.session import Base


class BaseModel(Base):
    """
    Clase base para todos los modelos SQLAlchemy.
    Incluye campos comunes y funcionalidades compartidas.
    """
    __abstract__ = True
    
    # Establecer el esquema automáticamente basado en la configuración
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
    
    # Propiedades comunes para todos los modelos
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), 
                        onupdate=func.now(), nullable=False)
    
    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el modelo a un diccionario"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            
            # Conversión de tipos especiales
            if isinstance(value, uuid.UUID):
                value = str(value)
            elif isinstance(value, datetime):
                value = value.isoformat()
                
            result[column.name] = value
        return result
    
    def update(self, **kwargs: Any) -> None:
        """Actualiza el modelo con los valores proporcionados"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

# class AuditableMixin:
#     """
#     Mixin para modelos que requieren auditoría.
#     Agrega campos para seguimiento de cambios.
#     """
#     created_by = Column(UUID(as_uuid=True), nullable=True)
#     updated_by = Column(UUID(as_uuid=True), nullable=True)
#     deleted_at = Column(DateTime(timezone=True), nullable=True)
#     deleted_by = Column(UUID(as_uuid=True), nullable=True)
#     is_deleted = Column(DateTime(timezone=True), nullable=True)

#     def soft_delete(self, user_id: Optional[uuid.UUID] = None) -> None:
#         """Realiza un borrado lógico del registro"""
#         self.deleted_at = datetime.now(timezone.utc)
#         self.deleted_by = user_id
#         self.is_deleted = True

class SearchableMixin:
    """
    Mixin para modelos que requieren búsqueda de texto completo.
    """
    texto_busqueda = Column(Text, nullable=True)
