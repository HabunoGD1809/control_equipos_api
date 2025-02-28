from fastapi import APIRouter

from app.api.routes import auth, usuarios, equipos, movimientos, mantenimiento

# Router principal para agrupar todos los endpoints
api_router = APIRouter()

# Rutas de autenticación
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Autenticación"]
)

# Rutas de usuarios
api_router.include_router(
    usuarios.router,
    prefix="/usuarios",
    tags=["Usuarios"]
)

# Rutas de equipos
api_router.include_router(
    equipos.router,
    prefix="/equipos",
    tags=["Equipos"]
)

# Rutas de movimientos
api_router.include_router(
    movimientos.router,
    prefix="/movimientos",
    tags=["Movimientos"]
)

# Rutas de mantenimiento
api_router.include_router(
    mantenimiento.router,
    prefix="/mantenimiento",
    tags=["Mantenimiento"]
)
