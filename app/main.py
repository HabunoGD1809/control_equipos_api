from contextlib import asynccontextmanager
import os
import time
from typing import Callable

from sqlalchemy import text

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from colorama import init as colorama_init, Fore, Style

from app.api.routes import api_router
from app.config import settings
from app.core.error_handlers import setup_error_handlers
from app.core.logging import get_logger, setup_logging
from app.db.session import engine

# Inicializar logging
setup_logging()
logger = get_logger(__name__)

# Inicializar colorama
colorama_init(autoreset=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Eventos de inicio y finalización de la aplicación.
    
    Args:
        app: Instancia de FastAPI
    """
    # Evento de inicio
    logger.info(f"{Fore.GREEN}Iniciando API de Control de Equipos{Style.RESET_ALL}")
    
    # Verificar conexión a la base de datos
    try:
        logger.info("Verificando conexión a la base de datos...")
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info(f"{Fore.GREEN}Conexión a la base de datos establecida correctamente{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"{Fore.RED}Error al conectar con la base de datos: {str(e)}{Style.RESET_ALL}")
        raise
    
    # Iniciar workers para tareas en segundo plano
    from app.worker import start_worker
    # Importar tareas de forma explícita en lugar de usar wildcard
    from app.tasks.notifications import send_notification, send_bulk_notifications
    from app.tasks.maintenance import check_upcoming_maintenances, check_expired_maintenances
    from app.tasks.reports import generate_equipment_status_report
    
    workers = []
    if os.environ.get("ENABLE_WORKERS", "true").lower() == "true":
        logger.info("Iniciando workers para tareas en segundo plano...")
        workers = await start_worker(num_workers=3)
        logger.info(f"{Fore.GREEN}Workers iniciados correctamente{Style.RESET_ALL}")
    
    yield
    
    # Evento de finalización
    logger.info(f"{Fore.YELLOW}Cerrando API de Control de Equipos{Style.RESET_ALL}")
    
    # Cerrar workers
    if workers:
        from app.worker import shutdown_worker
        logger.info("Cerrando workers...")
        await shutdown_worker(workers)
        logger.info("Workers cerrados correctamente")
    
    # Cerrar conexiones a la base de datos
    await engine.dispose()
    logger.info("Conexiones a la base de datos cerradas")


# Crear la aplicación FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Middleware para registro de tiempo de respuesta
@app.middleware("http")
async def add_process_time_header(request: Request, call_next: Callable):
    """
    Middleware para medir y registrar el tiempo de respuesta.
    
    Args:
        request: Solicitud HTTP
        call_next: Función para procesar la solicitud
        
    Returns:
        Respuesta HTTP
    """
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        # Registrar tiempo de respuesta para peticiones lentas (más de 1 segundo)
        if process_time > 1:
            logger.warning(f"Petición lenta: {request.method} {request.url.path} - {process_time:.4f}s")
            
        return response
    except Exception as e:
        logger.exception(f"Error no controlado: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Error interno del servidor"}
        )


# Configurar manejadores de errores
setup_error_handlers(app)

# Agregar rutas API
app.include_router(api_router, prefix=settings.API_V1_STR)

# Servir archivos estáticos (por ejemplo, documentación)
try:
    os.makedirs("static", exist_ok=True)
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    logger.warning(f"Error al montar archivos estáticos: {str(e)}")


if __name__ == "__main__":
    """
    Punto de entrada para ejecutar la aplicación directamente.
    """
    print(f"{Fore.CYAN}Control de Equipos API{Style.RESET_ALL}")
    print(f"Versión: {Fore.GREEN}{settings.VERSION}{Style.RESET_ALL}")
    print(f"Documentación: {Fore.YELLOW}http://localhost:8000{settings.API_V1_STR}/docs{Style.RESET_ALL}")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
