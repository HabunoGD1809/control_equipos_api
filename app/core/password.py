from passlib.context import CryptContext

# Configuración para hashing de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si la contraseña en texto plano coincide con el hash almacenado.
    """
    # La base de datos usa bcrypt para hashing que comienza con $2a$, $2b$ o $2y$
    if not hashed_password.startswith(('$2a$', '$2b$', '$2y$')):
        return False
    
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Genera un hash seguro para la contraseña.
    """
    return pwd_context.hash(password)
