import os
from typing import Any, Dict, Optional
from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Cargar variables de entorno desde archivo .env
load_dotenv()

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Control de Equipos API"
    DESCRIPTION: str = "API para el sistema de control y gestión de equipos"
    VERSION: str = "1.0.0"
    
    # Entorno de ejecución
    ENVIRONMENT: str = os.getenv("ENVIRONMENT")
    
    # Configuración JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 días
    
    # Configuración de base de datos
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB")
    POSTGRES_SCHEMA: str = os.getenv("POSTGRES_SCHEMA")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT")
    SQLALCHEMY_DATABASE_URI: Optional[PostgresDsn] = None

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",  # React frontend
        "http://localhost:8080",  # Vue.js alternative
        "http://localhost:4200",  # Angular alternative
        "http://localhost",
        "https://localhost",
        "http://localhost:8000",  # Para desarrollo
    ]
    
    # Configuración de logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "app.log")
    
    # Configuraciones de integración con S3 (para documentos)
    S3_BUCKET_NAME: Optional[str] = os.getenv("S3_BUCKET_NAME")
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    
    # Configuración de correo electrónico (para notificaciones)
    MAIL_SERVER: Optional[str] = os.getenv("MAIL_SERVER")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USERNAME: Optional[str] = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD: Optional[str] = os.getenv("MAIL_PASSWORD")
    MAIL_FROM: Optional[str] = os.getenv("MAIL_FROM")
    MAIL_TLS: bool = True
    MAIL_SSL: bool = False
    
    # Versión de API para versionado
    API_VERSION: str = "v1"

    # Validación y construcción de la URL de la base de datos
    @field_validator("SQLALCHEMY_DATABASE_URI", mode='before')
    def assemble_db_connection(cls, v: Optional[str], info: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
            
        values = info.data
        postgres_dsn = PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_SERVER"),
            port=int(values.get("POSTGRES_PORT", 5433)),
            path=f"{values.get('POSTGRES_DB') or ''}",
        )
        
        return postgres_dsn

    class Config:
        case_sensitive = True
        env_file = ".env"


# Instancia de configuración para usar en toda la aplicación
settings = Settings()
