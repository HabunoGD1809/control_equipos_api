from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession
from app.config import settings
from app.core.security import create_access_token

from app.core.password import get_password_hash, verify_password

from app.db.session import get_db
from app.schemas.token import (
    LoginRequest, 
    PasswordResetConfirm, 
    PasswordResetRequest, 
    Token
)
from app.services.usuarios import (
    get_user_by_email, 
    get_user_by_username, 
    update_user,
    register_login_attempt
)

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    db: DbSession
) -> Any:
    """
    Iniciar sesión en el sistema.
    
    Args:
        login_data: Credenciales de inicio de sesión
        db: Sesión de base de datos
        
    Returns:
        Token de acceso
    """
    user = await get_user_by_username(db, login_data.username)
    if not user:
        # Registrar intento fallido (sin usuario)
        await register_login_attempt(db, None, False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not verify_password(login_data.password, user["contrasena"]):
        # Registrar intento fallido
        await register_login_attempt(db, user["id"], False)
        
        # Incrementar contador de intentos fallidos
        user["intentos_fallidos"] += 1
        if user["intentos_fallidos"] >= 5:
            user["bloqueado"] = True
        
        await update_user(db, user_id=user["id"], obj_in={
            "intentos_fallidos": user["intentos_fallidos"],
            "bloqueado": user["bloqueado"]
        })
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if user["bloqueado"]:
        await register_login_attempt(db, user["id"], False)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario bloqueado. Contacte al administrador.",
        )
    
    # Registrar intento exitoso
    await register_login_attempt(db, user["id"], True)
    
    # Actualizar último login y resetear intentos fallidos
    await update_user(db, user_id=user["id"], obj_in={
        "ultimo_login": datetime.now(timezone.utc),
        "intentos_fallidos": 0
    })
    
    # Crear token de acceso
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user["nombre_usuario"], expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/login/form", response_model=Token)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Iniciar sesión con el formulario estándar OAuth2.
    Esta ruta es utilizada por el esquema OAuth2PasswordBearer de FastAPI.
    
    Args:
        form_data: Formulario de inicio de sesión
        db: Sesión de base de datos
        
    Returns:
        Token de acceso
    """
    user = await get_user_by_username(db, form_data.username)
    if not user:
        await register_login_attempt(db, None, False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not verify_password(form_data.password, user["contrasena"]):
        await register_login_attempt(db, user["id"], False)
        
        user["intentos_fallidos"] += 1
        if user["intentos_fallidos"] >= 5:
            user["bloqueado"] = True
        
        await update_user(db, user_id=user["id"], obj_in={
            "intentos_fallidos": user["intentos_fallidos"],
            "bloqueado": user["bloqueado"]
        })
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if user["bloqueado"]:
        await register_login_attempt(db, user["id"], False)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario bloqueado. Contacte al administrador.",
        )
    
    await register_login_attempt(db, user["id"], True)
    
    await update_user(db, user_id=user["id"], obj_in={
        "ultimo_login": datetime.now(timezone.utc),
        "intentos_fallidos": 0
    })
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user["nombre_usuario"], expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/password-reset", status_code=status.HTTP_200_OK)
async def request_password_reset(
    reset_data: PasswordResetRequest,
    db: DbSession
) -> Any:
    """
    Solicitar restablecimiento de contraseña.
    
    Args:
        reset_data: Datos para restablecimiento de contraseña
        db: Sesión de base de datos
        
    Returns:
        Mensaje de confirmación
    """
    user = await get_user_by_email(db, reset_data.email)
    if not user:
        # No revelar si el correo existe o no (prevención de enumeración)
        return {"message": "Si el correo está registrado, recibirá instrucciones para restablecer su contraseña."}
    
    # Generar token temporal
    token = await generate_password_reset_token(db, user["id"])
    
    # Deberia enviar un correo con el token
    # Para este ejemplo, simplemente devolvemos un mensaje
    
    return {"message": "Si el correo está registrado, recibirá instrucciones para restablecer su contraseña."}


@router.post("/password-reset/confirm", status_code=status.HTTP_200_OK)
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: DbSession
) -> Any:
    """
    Confirmar restablecimiento de contraseña.
    
    Args:
        reset_data: Datos para confirmar restablecimiento
        db: Sesión de base de datos
        
    Returns:
        Mensaje de confirmación
    """
    if reset_data.new_password != reset_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Las contraseñas no coinciden",
        )
    
    user = await get_user_by_reset_token(db, reset_data.token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido o expirado",
        )
    
    # Actualizar contraseña
    hashed_password = get_password_hash(reset_data.new_password)
    await update_user(db, user_id=user["id"], obj_in={
        "contrasena": hashed_password,
        "token_temporal": None,
        "token_expiracion": None,
        "requiere_cambio_contrasena": False
    })
    
    return {"message": "Contraseña actualizada correctamente"}


# Funciones auxiliares
async def generate_password_reset_token(db: AsyncSession, user_id: str) -> str:
    """
    Genera un token para restablecimiento de contraseña.
    
    Args:
        db: Sesión de base de datos
        user_id: ID del usuario
        
    Returns:
        Token generado
    """
    # En una implementación real, esta función generaría un token
    # y lo asociaría al usuario en la base de datos
    from uuid import uuid4
    token = str(uuid4())
    
    # Actualizar usuario con el token
    expiracion = datetime.now(timezone.utc) + timedelta(hours=24)
    await update_user(db, user_id=user_id, obj_in={
        "token_temporal": token,
        "token_expiracion": expiracion
    })
    
    return token


async def get_user_by_reset_token(db: AsyncSession, token: str) -> Any:
    """
    Obtiene un usuario por su token de restablecimiento.
    
    Args:
        db: Sesión de base de datos
        token: Token de restablecimiento
        
    Returns:
        Usuario si el token es válido, None en caso contrario
    """
    # En una implementación real, esta función buscaría al usuario
    # con el token proporcionado y verificaría que no haya expirado
    # Para este ejemplo, simplemente devolvemos None
    return None
