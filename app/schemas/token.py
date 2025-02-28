from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class Token(BaseModel):
    """Esquema para un token de acceso."""
    access_token: str
    token_type: str
    expires_in: int = Field(..., description="Tiempo de expiración en segundos")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 691200  # 8 días en segundos
            }
        }


class TokenPayload(BaseModel):
    """Esquema para el payload de un token JWT."""
    sub: Optional[str] = None
    exp: int = Field(..., description="Tiempo de expiración del token (timestamp)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "sub": "john_doe",
                "exp": 1719792000  # 30 de junio de 2025
            }
        }


class LoginRequest(BaseModel):
    """Esquema para la solicitud de inicio de sesión."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "password": "securePassword123"
            }
        }


class PasswordResetRequest(BaseModel):
    """Esquema para la solicitud de restablecimiento de contraseña."""
    email: EmailStr
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@example.com"
            }
        }


class PasswordResetConfirm(BaseModel):
    """Esquema para confirmar el restablecimiento de contraseña."""
    token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "550e8400-e29b-41d4-a716-446655440000",
                "new_password": "newSecurePassword123",
                "confirm_password": "newSecurePassword123"
            }
        }
