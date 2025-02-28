from typing import Annotated, List

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import get_current_active_user, check_user_permissions
from app.db.session import get_db

# Configuración para autenticación
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

# Dependencias para inyectar en las rutas
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_active_user)]


def get_current_user_with_permissions(required_permissions: List[str]):
    """
    Dependencia que verifica que el usuario actual tenga los permisos requeridos.
    
    Args:
        required_permissions: Lista de permisos requeridos
        
    Returns:
        Dependencia para inyectar en las rutas
    """
    async def _get_current_user_with_permissions(
        security_scopes: SecurityScopes,
        current_user: CurrentUser
    ) -> dict:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No autenticado",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        has_permissions = await check_user_permissions(current_user, required_permissions)
        
        if not has_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permisos insuficientes. Se requieren: {', '.join(required_permissions)}",
            )
            
        return current_user
        
    return _get_current_user_with_permissions


AdminUser = Annotated[dict, Depends(
    get_current_user_with_permissions(["administrar_usuarios"])
)]
EquiposReadUser = Annotated[dict, Depends(
    get_current_user_with_permissions(["ver_equipos"])
)]
EquiposWriteUser = Annotated[dict, Depends(
    get_current_user_with_permissions(["editar_equipos"])
)]
MovimientosUser = Annotated[dict, Depends(
    get_current_user_with_permissions(["registrar_movimientos"])
)]
MovimientosAuthUser = Annotated[dict, Depends(
    get_current_user_with_permissions(["autorizar_movimientos"])
)]
MantenimientosReadUser = Annotated[dict, Depends(
    get_current_user_with_permissions(["ver_mantenimientos"])
)]
MantenimientosWriteUser = Annotated[dict, Depends(
    get_current_user_with_permissions(["programar_mantenimientos"])
)]
DocumentosReadUser = Annotated[dict, Depends(
    get_current_user_with_permissions(["ver_documentos"])
)]
DocumentosWriteUser = Annotated[dict, Depends(
    get_current_user_with_permissions(["subir_documentos"])
)]
DocumentosVerifyUser = Annotated[dict, Depends(
    get_current_user_with_permissions(["verificar_documentos"])
)]
ReportesUser = Annotated[dict, Depends(
    get_current_user_with_permissions(["generar_reportes"])
)]
AuditoriaUser = Annotated[dict, Depends(
    get_current_user_with_permissions(["ver_auditoria"])
)]
