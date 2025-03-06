import uuid
from datetime import datetime
from typing import Any, Dict, Union, Callable, Type

from sqlalchemy import Column, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr

from app.db.session import Base

class TimestampMixin:
    """
    Mixin: permite configurar qué campos timestamp se desean:
    - created_at: timestamp de creación
    - updated_at: timestamp de última actualización
    """
    created_at: Union[Column, None] = None
    updated_at: Union[Column, None] = None

    @classmethod
    def with_created_at(cls) -> Type['TimestampMixin']:
        """
        Añade solo el campo created_at al modelo.
        
        Returns:
            La clase con el campo created_at añadido.
        """
        if not hasattr(cls, 'created_at'):
            cls.created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
        return cls

    @classmethod
    def with_updated_at(cls) -> Type['TimestampMixin']:
        """
        Añade solo el campo updated_at al modelo.
        
        Returns:
            La clase con el campo updated_at añadido.
        """
        if not hasattr(cls, 'updated_at'):
            cls.updated_at = Column(DateTime(timezone=True), server_default=func.now(), 
                                    onupdate=func.now(), nullable=False)
        return cls

    @classmethod
    def with_timestamps(cls) -> Type['TimestampMixin']:
        """
        Añade tanto created_at como updated_at al modelo.
        
        Returns:
            La clase con ambos campos de timestamp.
        """
        cls.with_created_at()
        cls.with_updated_at()
        return cls

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
    
    # Solo el ID como campo común
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
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
