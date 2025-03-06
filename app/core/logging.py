from __future__ import annotations
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

from loguru import logger
from pydantic import BaseModel

from app.config import settings

if TYPE_CHECKING:
    from loguru import Logger

# Configuración de formatos para diferentes niveles de log
LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
ERROR_FORMAT = "<red>{time:YYYY-MM-DD HH:mm:ss}</red> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

# Crear directorio de logs si no existe
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Nombre del archivo de log con fecha
log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}_{settings.LOG_FILE}"


class InterceptHandler(logging.Handler):
    """
    Interceptor para integrar loguru con la biblioteca logging estándar.
    Permite que las librerías que usan logging envíen sus logs a loguru.
    """
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


class LogConfig(BaseModel):
    """Configuración de logging para la aplicación."""
    LOGGER_NAME: str = "api_logger"
    LOG_FORMAT: str = LOG_FORMAT
    ERROR_FORMAT: str = ERROR_FORMAT
    LOG_LEVEL: str = settings.LOG_LEVEL
    LOG_FILE: str = str(log_file)

    # Valores por defecto para loggers específicos
    LOGGERS: Dict[str, Dict[str, Any]] = {
        "uvicorn": {"level": "INFO"},
        "uvicorn.error": {"level": "INFO"},
        "uvicorn.access": {"level": "INFO"},
        "sqlalchemy.engine": {"level": "WARNING"},
        "sqlalchemy.pool": {"level": "WARNING"},
        "alembic": {"level": "INFO"},
        "fastapi": {"level": "INFO"},
    }


def setup_logging() -> None:
    """Configura el sistema de logging para la aplicación."""
    config = LogConfig()
    
    # Remover handlers existentes
    logger.remove()
    
    # Configurar salida a consola
    logger.add(
        sys.stdout,
        format=config.LOG_FORMAT,
        level=config.LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
    
    # Configurar salida a archivo
    logger.add(
        config.LOG_FILE,
        format=config.LOG_FORMAT,
        level=config.LOG_LEVEL,
        rotation="10 MB",  # Rotar cuando el archivo alcanza 10MB
        retention="30 days",  # Mantener logs por 30 días
        compression="zip",  # Comprimir archivos rotados
        backtrace=True,
        diagnose=True,
    )
    
    # Interceptar logs de librerías estándar
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Configurar loggers específicos
    for logger_name, logger_config in config.LOGGERS.items():
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.setLevel(logger_config["level"])
        logging_logger.propagate = False

    # Log de inicio del sistema
    logger.info("Sistema de logging inicializado")


def get_logger(name: Optional[str] = None) -> Logger:
    """
    Obtiene un logger configurado para un módulo específico.
    
    Args:
        name: Nombre del módulo para el logger
        
    Returns:
        Un logger configurado
    """
    return logger.bind(name=name)
