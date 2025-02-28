from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
import uuid

from fastapi import Query
from pydantic import BaseModel, Field

# Tipo genérico para modelos
T = TypeVar('T')


class Mensaje(BaseModel):
    """Esquema para respuestas de mensaje simple."""
    detail: str


class PaginacionParams:
    """Parámetros comunes para paginación."""
    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Número de registros a omitir"),
        limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros a devolver")
    ):
        self.skip = skip
        self.limit = limit


class PaginatedResponse(BaseModel, Generic[T]):
    """Respuesta paginada genérica."""
    items: List[T]
    total: int
    page: int
    size: int
    pages: int
    
    @classmethod
    def create(cls, items: List[T], total: int, page: int, size: int) -> 'PaginatedResponse[T]':
        """
        Crea una respuesta paginada.
        
        Args:
            items: Lista de elementos
            total: Total de elementos (sin paginación)
            page: Página actual (1-based)
            size: Tamaño de página
            
        Returns:
            Respuesta paginada
        """
        pages = (total + size - 1) // size if size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages
        )


class SearchParams:
    """Parámetros comunes para búsqueda."""
    def __init__(
        self,
        q: Optional[str] = Query(None, min_length=1, description="Término de búsqueda"),
        skip: int = Query(0, ge=0, description="Número de registros a omitir"),
        limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros a devolver")
    ):
        self.q = q
        self.skip = skip
        self.limit = limit


class ItemResponse(BaseModel, Generic[T]):
    """Respuesta para un único elemento."""
    data: T


class ItemsResponse(BaseModel, Generic[T]):
    """Respuesta para múltiples elementos."""
    data: List[T]


class ItemCreatedResponse(BaseModel):
    """Respuesta para un elemento creado."""
    id: uuid.UUID
    message: str = "Elemento creado correctamente"


class ItemUpdatedResponse(BaseModel):
    """Respuesta para un elemento actualizado."""
    id: uuid.UUID
    message: str = "Elemento actualizado correctamente"


class ItemDeletedResponse(BaseModel):
    """Respuesta para un elemento eliminado."""
    id: uuid.UUID
    message: str = "Elemento eliminado correctamente"


class ErrorResponse(BaseModel):
    """Respuesta de error detallada."""
    detail: str
    status_code: int
    errors: Optional[List[Dict[str, Any]]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Error de validación",
                "status_code": 422,
                "errors": [
                    {
                        "loc": ["body", "username"],
                        "msg": "field required",
                        "type": "value_error.missing"
                    }
                ]
            }
        }
