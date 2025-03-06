from datetime import datetime, timedelta, timezone
import uuid
from typing import Any, Dict, Optional, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db
from app.schemas.token import TokenPayload

# Configuración para autenticación
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/form" 
    
    # El endpoint compatible con el formato de formulario 
    # que Swagger necesita es /api/v1/auth/login/form 
    
)

def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crea un token JWT con los datos del usuario.
    
    Args:
        subject: Identificador del usuario (username o UUID)
        expires_delta: Tiempo de expiración opcional
        
    Returns:
        Token JWT codificado
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    # Datos a incluir en el token
    to_encode = {"exp": expire, "sub": str(subject)}
    
    # Codificar token con la clave secreta
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> Dict[str, Any]:
    """
    Valida el token JWT y obtiene el usuario actual.
    
    Args:
        db: Sesión de base de datos
        token: Token JWT
        
    Returns:
        Usuario autenticado
        
    Raises:
        HTTPException: Si el token es inválido o el usuario no existe
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decodificar el token
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Validar la estructura del token
        token_data = TokenPayload(**payload)
        
        if datetime.fromtimestamp(token_data.exp) < datetime.now().replace(tzinfo=None):
            raise credentials_exception
            
        # Extraer el identificador del usuario
        username: str = token_data.sub
        if not username:
            raise credentials_exception
            
    except (JWTError, ValidationError):
        raise credentials_exception
    
    # Importación tardía para evitar la circularidad
    from app.services.usuarios import get_user_by_username
        
    # Obtener el usuario desde la base de datos
    user = await get_user_by_username(db, username)
    
    if not user:
        raise credentials_exception
        
    if user.get("bloqueado"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario bloqueado. Contacte al administrador.",
        )
        
    return user


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Verifica que el usuario actual esté activo.
    
    Args:
        current_user: Usuario autenticado
        
    Returns:
        Usuario autenticado y activo
        
    Raises:
        HTTPException: Si el usuario está inactivo
    """
    if current_user.get("bloqueado"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )
    return current_user


async def check_user_permissions(
    current_user: Dict[str, Any],
    required_permissions: list[str],
) -> bool:
    """
    Verifica si el usuario tiene los permisos requeridos.
    
    Args:
        current_user: Usuario actual
        required_permissions: Lista de permisos requeridos
        
    Returns:
        True si el usuario tiene todos los permisos, False en caso contrario
    """
    # Si es administrador, siempre tiene permisos
    if current_user.get("rol", {}).get("nombre") == "admin":
        return True
    
    # Obtener los permisos del usuario
    user_permissions = []
    if "rol" in current_user and "permisos" in current_user["rol"]:
        user_permissions = [p["nombre"] for p in current_user["rol"]["permisos"]]
    
    # Verificar si el usuario tiene todos los permisos requeridos
    return all(permission in user_permissions for permission in required_permissions)


async def get_usuario_id_from_token(token: str) -> Optional[uuid.UUID]:
    """
    Extrae el ID de usuario del token JWT.
    
    Args:
        token: Token JWT
        
    Returns:
        UUID del usuario o None si el token es inválido
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        username: str = payload.get("sub")
        if not username:
            return None
        
        # En este caso, el subject es el nombre de usuario
        # Para obtener el UUID, debería consultarse la BD
        # Pero para simplificar, asumimos que es un UUID
        try:
            return uuid.UUID(username)
        except ValueError:
            # Si no es un UUID, retornamos None
            return None
            
    except JWTError:
        return None
