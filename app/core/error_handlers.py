from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import Any, Dict, Optional, Union

from app.core.logging import get_logger

# Configuración de logger
logger = get_logger(__name__)


class APIError(Exception):
    """
    Excepción base para errores de API personalizados.
    Permite definir el código de estado, detalles y encabezados HTTP.
    """
    def __init__(
        self,
        status_code: int,
        detail: Union[str, Dict[str, Any]],
        headers: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.detail = detail
        self.headers = headers


class NotFoundError(APIError):
    """Recurso no encontrado (404)"""
    def __init__(
        self,
        detail: Union[str, Dict[str, Any]] = "Recurso no encontrado",
        headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status.HTTP_404_NOT_FOUND, detail, headers)


class BadRequestError(APIError):
    """Solicitud incorrecta (400)"""
    def __init__(
        self,
        detail: Union[str, Dict[str, Any]] = "Solicitud incorrecta",
        headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status.HTTP_400_BAD_REQUEST, detail, headers)


class ForbiddenError(APIError):
    """Acceso prohibido (403)"""
    def __init__(
        self,
        detail: Union[str, Dict[str, Any]] = "Acceso prohibido",
        headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status.HTTP_403_FORBIDDEN, detail, headers)


class ConflictError(APIError):
    """Conflicto con el estado actual del recurso (409)"""
    def __init__(
        self,
        detail: Union[str, Dict[str, Any]] = "Conflicto con el estado actual del recurso",
        headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status.HTTP_409_CONFLICT, detail, headers)


class UnauthorizedError(APIError):
    """No autorizado (401)"""
    def __init__(
        self,
        detail: Union[str, Dict[str, Any]] = "No autorizado",
        headers: Optional[Dict[str, Any]] = None
    ):
        if not headers:
            headers = {"WWW-Authenticate": "Bearer"}
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail, headers)


class ServerError(APIError):
    """Error interno del servidor (500)"""
    def __init__(
        self,
        detail: Union[str, Dict[str, Any]] = "Error interno del servidor",
        headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status.HTTP_500_INTERNAL_SERVER_ERROR, detail, headers)


def setup_error_handlers(app: FastAPI) -> None:
    """
    Configura los manejadores de errores para la aplicación FastAPI.
    
    Args:
        app: Instancia de la aplicación FastAPI
    """
    
    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
        """Manejador para excepciones personalizadas APIError"""
        logger.error(f"API Error: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Manejador para errores de validación de esquemas"""
        errors = []
        for error in exc.errors():
            error_info = {
                "loc": error["loc"],
                "msg": error["msg"],
                "type": error["type"],
            }
            errors.append(error_info)
        
        logger.warning(f"Validation Error: {errors}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Error de validación",
                "errors": errors
            },
        )
    
    @app.exception_handler(ValidationError)
    async def pydantic_validation_error_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        """Manejador para errores de validación de Pydantic"""
        errors = []
        for error in exc.errors():
            error_info = {
                "loc": error["loc"],
                "msg": error["msg"],
                "type": error["type"],
            }
            errors.append(error_info)
        
        logger.warning(f"Pydantic Validation Error: {errors}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Error de validación de datos",
                "errors": errors
            },
        )
    
    @app.exception_handler(IntegrityError)
    async def sqlalchemy_integrity_error_handler(
        request: Request, exc: IntegrityError
    ) -> JSONResponse:
        """Manejador para errores de integridad de SQLAlchemy"""
        error_detail = str(exc.orig) if hasattr(exc, 'orig') else str(exc)
        logger.error(f"Database Integrity Error: {error_detail}")
        
        # Detectar errores comunes y dar respuestas más amigables
        if "unique constraint" in error_detail.lower():
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "detail": "Registro duplicado",
                    "message": "Ya existe un registro con esos datos"
                },
            )
        
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": "Error de integridad en la base de datos",
                "message": error_detail
            },
        )
    
    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        """Manejador para errores generales de SQLAlchemy"""
        error_detail = str(exc)
        logger.error(f"Database Error: {error_detail}")
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Error en la base de datos",
                "message": "Error al procesar la operación en la base de datos"
            },
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Manejador para excepciones no capturadas"""
        error_detail = str(exc)
        logger.exception(f"Unhandled Exception: {error_detail}")
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Error interno del servidor",
                "message": "Se ha producido un error inesperado"
            },
        )
